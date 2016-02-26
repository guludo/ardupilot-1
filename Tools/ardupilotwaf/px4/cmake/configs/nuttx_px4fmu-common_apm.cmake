include(nuttx/px4_impl_nuttx)

set(CMAKE_TOOLCHAIN_FILE ${CMAKE_SOURCE_DIR}/cmake/toolchains/Toolchain-arm-none-eabi.cmake)

set(config_module_list
	platforms/common
	platforms/nuttx
	modules/param
#
# Board support modules
#
	drivers/device
	drivers/stm32
	drivers/stm32/adc
	drivers/stm32/tone_alarm
	drivers/led
	drivers/px4fmu
	drivers/rgbled
	drivers/mpu6000
	drivers/hmc5883
	drivers/ms5611
	drivers/mb12xx
	drivers/ll40ls
	drivers/trone
	#drivers/gps
	#drivers/hil
	#drivers/hott_telemetry
	#drivers/blinkm
	#modules/sensors
	drivers/airspeed
	drivers/ets_airspeed
	drivers/meas_airspeed
	drivers/mkblctrl
	drivers/batt_smbus
	drivers/irlock

#
# System commands
#
	systemcmds/bl_update
	systemcmds/mixer
	systemcmds/perf
	systemcmds/pwm
	systemcmds/reboot
	systemcmds/top
	#systemcmds/tests
	systemcmds/nshterm
	systemcmds/mtd
	systemcmds/ver
	systemcmds/reflect
	systemcmds/motor_test
	systemcmds/usb_connected

#
# Library modules
#
	modules/systemlib
	modules/systemlib/mixer
	modules/uORB
	lib/mathlib/math/filter
	lib/conversion
)

set(config_extra_builtin_cmds
	serdis
	sercon
)

set(config_io_board
	px4io-v2
)

set(config_extra_libs
	${CMAKE_SOURCE_DIR}/src/lib/mathlib/CMSIS/libarm_cortexM4lf_math.a
    ${APM_PROGRAM_LIB}
)

add_custom_target(sercon)
set_target_properties(sercon PROPERTIES
	MAIN "sercon" STACK "2048")

add_custom_target(serdis)
set_target_properties(serdis PROPERTIES
	MAIN "serdis" STACK "2048")
