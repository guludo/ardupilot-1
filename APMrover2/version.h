#pragma once

#ifdef WAF_BUILD_SYSTEM
#include "ap_version.h"
#endif

#define THISFIRMWARE "ArduRover v3.0.0"
#define FIRMWARE_VERSION 3,0,0,FIRMWARE_VERSION_TYPE_OFFICIAL

#ifndef GIT_VERSION
#define FIRMWARE_STRING THISFIRMWARE
#else
#define FIRMWARE_STRING THISFIRMWARE " (" GIT_VERSION ")"
#endif
