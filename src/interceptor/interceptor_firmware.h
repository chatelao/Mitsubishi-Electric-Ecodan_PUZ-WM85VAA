/**
 * @file interceptor_firmware.h
 * @brief RP2350 Dual-Channel Interceptor Board Embedded Firmware Header
 */

#ifndef INTERCEPTOR_FIRMWARE_H
#define INTERCEPTOR_FIRMWARE_H

#include <stdint.h>
#include <stdbool.h>

/* Hardware Constants & Ratios */
#define DIVIDER_RATIO 0.50f     /* R1=10k, R2=10k -> 10/20 */
#define OPAMP_GAIN    2.00f     /* Non-inverting G = 1 + 10k/10k = 2.0 */
#define DEFAULT_K_ATTEN 0.68f   /* Acoustic attenuation factor */
#define MIN_K_ATTEN    0.68f
#define MAX_K_ATTEN    1.00f

/* Signal Thresholds */
#define VSP_STALL_VOLTAGE_MIN  1.80f  /* Minimum Vsp voltage where motor should spin */
#define VSP_BYPASS_VOLTAGE_MAX 5.20f  /* Vsp_in threshold for high-load emergency bypass */
#define FG_STALL_FREQ_HZ_MIN   10.0f  /* Below this Hz while Vsp > 1.8V indicates stall */
#define NTC_FREEZE_TEMP_C_MIN  -3.0f  /* T_evap below this triggers freeze override bypass */

/* RP2350 ADC / DAC / PWM Definitions (3.3V VDD Reference) */
#define ADC_REF_VOLTAGE 3.30f
#define ADC_MAX_COUNT   4095.0f
#define DAC_MAX_COUNT   4095.0f
#define DAC_REF_VOLTAGE 3.30f

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
