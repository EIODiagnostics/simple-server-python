#include "boson_stream.h"

struct v4l2_requestbuffers request_buffer;
struct v4l2_capability capability;
struct v4l2_buffer query_buffer;
struct v4l2_format video_format;
unsigned char * current_frame;
pthread_t callback_thread;
int current_frame_length;
void * buffer_start;
float frame_pause;
sem_t frame_lock;
int video_mode;
int stopped;
int fd;

BOSON_RESULT boson_linear_agc(char *input_16, char *output_8, int width, int height) {
  unsigned int byte1, byte2, byte3, byte4;
  unsigned int max = 0x0000;
  unsigned int min = 0xFFFF;
  int i, j;

  for (i = 0; i < height; i++) {
    for (j = 0; j < width; j++) {
      // Combine two bytes of data into a single 2-byte unsigned integer.
      byte1 =  input_16[(((i * width) + j) * 2) + 1] & 0xFF;
      byte2 =  input_16[(((i * width) + j) * 2)]     & 0xFF;
      byte3 = (byte1 << 8) + byte2;

      // Locate the minimal value in the buffer.
      if (byte3 <= min) min = byte3;

      // Locate the maximal value in the buffer.
      if (byte3 >= max) max = byte3;
    }
  }

  for (i = 0; i < height; i++) {
    for (j = 0; j < width; j++) {
      byte1 = input_16[(((i * width) + j) * 2) + 1] & 0xFF;
      byte2 = input_16[(((i * width) + j) * 2)]     & 0xFF;
      byte3 = (byte1 << 8) + byte2;

      // Scale the number down to an 8-bit output.
      if ((max - min) == 0) {
        byte4 = 0;
      } else {
        byte4 = ((255 * (byte3 - min))) / (max - min);
      }

      output_8[(i * width) + j] = (unsigned char)(byte4 & 0xFF);
    }
  }
  
  return BOSON_SUCCESS;
}

BOSON_RESULT boson_stream_initialize(char *device) { 
  int res;

  /* Attempt to open the specified video device. */
  if((fd = open(device, O_RDWR)) < 0){
    fprintf(stderr, "Error: unable to open device: %s\n", device);
    return BOSON_ERROR_INVALID_DEVICE;
  }

  /* Check if video capture mode is available. */
  if((res = ioctl(fd, VIDIOC_QUERYCAP, &capability)) < 0){
    fprintf(stderr, "Error: this device does not have video capture capabilities.\n");
    return BOSON_ERROR_NO_CAPABILITY;
  }
  
  if(! (capability.capabilities & V4L2_CAP_VIDEO_CAPTURE)){
    fprintf(stderr, "Error: this device does not handle single-planar video capture.\n");
    return BOSON_ERROR_NO_CAPABILITY;
  }

  /* Set the output format for the video. */
  video_format.fmt.pix.pixelformat = V4L2_PIX_FMT_Y16;
  video_format.fmt.pix.height      = VIDEO_HEIGHT;
  video_format.fmt.pix.width       = VIDEO_WIDTH;
  video_format.type                = V4L2_BUF_TYPE_VIDEO_CAPTURE;
  
  if (ioctl(fd, VIDIOC_S_FMT, &video_format) < 0){
    fprintf(stderr, "Error: unable to set format for video output.\n");
    BOSON_ERROR_NO_CAPABILITY;
  }

  /* Set up and initialize the request buffer we'll use to receive data from
   * the camera.
   */
  request_buffer.type   = V4L2_BUF_TYPE_VIDEO_CAPTURE;
  request_buffer.memory = V4L2_MEMORY_MMAP;
  request_buffer.count  = 1;

  if (ioctl(fd, VIDIOC_REQBUFS, &request_buffer) < 0){
    fprintf(stderr, "Error: unable to allocate request buffers.");
    return BOSON_ERROR_REQUEST_BUFFER;
  }

  memset(&query_buffer, 0, sizeof(query_buffer));

  query_buffer.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
  query_buffer.memory = V4L2_MEMORY_MMAP;
  query_buffer.index = 0;

  if(ioctl(fd, VIDIOC_QUERYBUF, &query_buffer) < 0){
    fprintf(stderr, "Error: unable to allocate query buffers.");
    exit(1);
  }

  buffer_start = mmap(NULL, query_buffer.length, PROT_READ | PROT_WRITE,MAP_SHARED, fd, query_buffer.m.offset);

  if (buffer_start == MAP_FAILED) {
    fprintf(stderr, "Error: unable to mmap query buffer\n");
    return BOSON_ERROR_QUERY_BUFFER;
  }

  memset(buffer_start, 0, query_buffer.length);

  /* We're going to use a semaphore to restrict access to the current_frame
   * array since we'll have multiple threads reading/writing to it at the
   * same time, and we want the data to be current and complete.
   */
  res = sem_init(&frame_lock, 0, 1);
  
  frame_pause = 0;
  
  stopped = 1;
  
  return BOSON_SUCCESS;
}

void * callback_runner(void * arg) {
  void (* callback)(int, int, int, unsigned char *) = (void (*)(int, int, int, unsigned char *))arg;
  unsigned char * buffer;
  struct timespec pause;
  int length;
  int res;
  
  buffer = NULL;
  length = -1;

  pause.tv_sec = 0;
  pause.tv_nsec = (long)(frame_pause * 1000000000);
  
  do {
    /* Queue the empty query buffer into the incoming queue. */
    if(ioctl(fd, VIDIOC_QBUF, &query_buffer) < 0){
      fprintf(stderr, "Error: unable to queue query buffer:  %d\n", errno);
      return NULL;
    }

    /* Wait until the query buffer has been filled by the camera. */
    if(ioctl(fd, VIDIOC_DQBUF, &query_buffer) < 0) {
      fprintf(stderr, "Error: unable to dequeue query buffer:  %d\n", errno);
      return NULL;
    }

    /* Obtain a lock before accessing the current_frame. */
    res = sem_wait(&frame_lock);
    
    /* If we haven't had a query buffer allocated, or the buffer size has
     * changed, then allocate/reallocate space for the buffer getting
     * passed into the callback function.
     */
    if (length != query_buffer.length) {
      fprintf(stderr, "Setting query buffer length to: %d\n", query_buffer.length);
      length = query_buffer.length;
      if (buffer == NULL) {
        buffer = malloc(length);
        if (! buffer) {
          fprintf(stderr, "Error: unable to allocate query buffer\n");
          continue;
        }
      } else {
        buffer = realloc(buffer, length);
        if (! buffer) {
          fprintf(stderr, "Error: unable to reallocate query buffer\n");
          continue;
        }
      }

      /* We'll also need to update the length of the current frame buffer. */
      if (current_frame == NULL) {
	current_frame = malloc(length);
	if (! current_frame) {
	  fprintf(stderr, "Error: unable to allocate current frame buffer\n");
	  continue;
	}
      } else {
	current_frame = realloc(current_frame, length);
	if (! current_frame) {
	  fprintf(stderr, "Error: unable to reallocate current frame buffer\n");
	  continue;
	}
      }
    }

    memcpy(buffer, buffer_start, length);

    memcpy(current_frame, buffer_start, length);
    current_frame_length = length;
    
    /* Release the lock on the current_frame semaphore. */
    res = sem_post(&frame_lock);
    
    /* Run the callback, passing in the data frame as an argument. */
    (* callback)(VIDEO_WIDTH, VIDEO_HEIGHT, query_buffer.length, buffer);

    /* Pause for the specified number of seconds before retrieving the next
     * buffer.  We can control the framerate this way.
     */
    nanosleep(&pause, NULL);
  } while (! stopped);

  if (buffer != NULL) free(buffer);
}

BOSON_RESULT boson_current_frame(unsigned char *frame, int *length) {
  int res;
  
  /* Before accessing the current_frame, obtain a lock. */
  res = sem_wait(&frame_lock);

  *length = current_frame_length;
  memcpy(frame, current_frame, *length);  

  /* Release the lock on the current_frame. */
  res = sem_post(&frame_lock);
  
  return BOSON_SUCCESS;
}

BOSON_RESULT boson_stream_start(float pause, void (*callback)(int, int, int, unsigned char *)) {
  int type = query_buffer.type;

  if (ioctl(fd, VIDIOC_STREAMON, &type) < 0) {
    fprintf(stderr, "Error: unable to enable streaming\n");
    return BOSON_ERROR_INVALID_DEVICE;
  }

  // Ensure our interframe pause is a number >= 0.
  if (! (pause >= 0))
    return BOSON_ERROR_INVALID_PARAM;
  frame_pause = pause;

  stopped = 0;
  
  int res = pthread_create(&callback_thread, NULL, callback_runner, (void *)callback);

  return BOSON_SUCCESS;
}

BOSON_RESULT boson_stream_stop() {
  int type;

  stopped = 1;
  
  type = query_buffer.type;
  
  if( ioctl(fd, VIDIOC_STREAMOFF, &type) < 0 ){
    fprintf(stderr, "Error: unable to disable streaming\n");
    return BOSON_ERROR_INVALID_DEVICE;
  };
  
  return BOSON_SUCCESS;
}

BOSON_RESULT boson_stream_shutdown() {

  close(fd);
  
  return BOSON_SUCCESS;
}
