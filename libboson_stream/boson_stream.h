#ifndef __boson_h__
#define __boson_h__

#ifndef OSX 
#   include <linux/videodev2.h>
#   include <asm/types.h>
#endif

#include <semaphore.h>
#include <sys/ioctl.h>
#include <sys/types.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <pthread.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>

#define DEBUG 1

#define VIDEO_WIDTH  320
#define VIDEO_HEIGHT 256

#define VIDEO_MODE_YUV   0
#define VIDEO_MODE_RAW14 1

enum _return_codes {
  BOSON_SUCCESS               = 0,
  BOSON_ERROR_INVALID_DEVICE  = -1,
  BOSON_ERROR_NO_CAPABILITY   = -2,
  BOSON_ERROR_REQUEST_BUFFER  = -3,
  BOSON_ERROR_QUERY_BUFFER    = -4,
  BOSON_ERROR_VIDEO_MODE      = -5,
  BOSON_ERROR_NOT_INITIALIZED = -6,
  BOSON_ERROR_INVALID_PARAM   = -7,
  BOSON_ERROR_MEMORY_ALLOC    = -8
};
typedef enum _return_codes BOSON_RESULT;

BOSON_RESULT boson_linear_agc(char *input_16, char *output_8, int width, int height);
BOSON_RESULT boson_stream_initialize(char *device);
BOSON_RESULT boson_stream_start(float pause, void (*callback)(int width, int height, int length, unsigned char *buffer));
BOSON_RESULT boson_stream_stop();
BOSON_RESULT boson_stream_shutdown();

#endif
