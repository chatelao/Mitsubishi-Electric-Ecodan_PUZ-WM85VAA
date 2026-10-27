/**
 * @file interceptor_firmware.h
 * @brief ATtiny1616 Dual-Channel Interceptor Board Embedded Firmware Header
 */

#ifndef INTERCEPTOR_FIRMWARE_H
#define INTERCEPTOR_FIRMWARE_H

#include <stdint.h>
#include <stdbool.h>

/* Hardware Constants & Ratios */
#define DIVIDER_RATIO 0.6875f   /* R1=10k, R2=22k -> 22/32 */
#define OPAMP_GAIN    1.50f     /* Non-inverting G = 1 + 10k/20k = 1.5 */
#define DEFAULT_K_ATTEN 0.68f   /* Acoustic attenuation factor */
#define MIN_K_ATTEN    0.68f
#define MAX_K_ATTEN    1.00f

/* Signal Thresholds */
#define VSP_STALL_VOLTAGE_MIN  1.80f  /* Minimum Vsp voltage where motor should spin */
#define VSP_BYPASS_VOLTAGE_MAX 5.20f  /* Vsp_in threshold for high-load emergency bypass */
#define FG_STALL_FREQ_HZ_MIN   10.0f  /* Below this Hz while Vsp > 1.8V indicates stall */
#define NTC_FREEZE_TEMP_C_MIN  -3.0f  /* T_evap below this triggers freeze override bypass */

/* ATtiny1616 ADC / DAC Definitions (5.0V VDD Reference) */
#define ADC_REF_VOLTAGE 5.00f
#define ADC_MAX_COUNT   1023.0f
#define DAC_MAX_COUNT   255.0f
#define DAC_REF_VOLTAGE 4.34f

/* State Machine Modes */
typedef enum {
    INTERCEPTOR_MODE_NORMAL_INTERCEPT = 0,
    INTERCEPTOR_MODE_STALL_PASSTHROUGH,
    INTERCEPTOR_MODE_FREEZE_BYPASS,
    INTERCEPTOR_MODE_HIGH_LOAD_BYPASS,
    INTERCEPTOR_MODE_WDT_FAILSAFE
} InterceptorMode_t;

/* Channel Signal Structure */
typedef struct {
    float vsp_in_volts;
    float vsp_out_volts;
    float fg_in_freq_hz;
    float fg_out_freq_hz;
    bool stall_detected;
} ChannelState_t;

/* System Status Structure */
typedef struct {
    ChannelState_t ch1;
    ChannelState_t ch2;
    float t_evap_c;
    float k_attenuation;
    InterceptorMode_t mode;
    bool relay_bypass_active;
} InterceptorSystemState_t;

/* Function Declarations */
void interceptor_init(InterceptorSystemState_t *state);
void interceptor_update(InterceptorSystemState_t *state, float vsp_in1, float vsp_in2, float fg_in1, float fg_in2, float t_evap);
float calculate_vsp_out(float vsp_in, float k);
float calculate_fg_out(float fg_in, float k, float vsp_in, bool *stall_flag);

#endif /* INTERCEPTOR_FIRMWARE_H */
