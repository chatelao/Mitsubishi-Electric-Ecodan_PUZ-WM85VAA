/**
 * @file interceptor_firmware.c
 * @brief ATtiny1616 Dual-Channel Interceptor Board Embedded Firmware Implementation
 */

#include "interceptor_firmware.h"
#include <stddef.h>

void interceptor_init(InterceptorSystemState_t *state) {
    if (!state) return;
    state->ch1.vsp_in_volts = 0.0f;
    state->ch1.vsp_out_volts = 0.0f;
    state->ch1.fg_in_freq_hz = 0.0f;
    state->ch1.fg_out_freq_hz = 0.0f;
    state->ch1.stall_detected = false;

    state->ch2.vsp_in_volts = 0.0f;
    state->ch2.vsp_out_volts = 0.0f;
    state->ch2.fg_in_freq_hz = 0.0f;
    state->ch2.fg_out_freq_hz = 0.0f;
    state->ch2.stall_detected = false;

    state->t_evap_c = 20.0f;
    state->k_attenuation = DEFAULT_K_ATTEN;
    state->mode = INTERCEPTOR_MODE_NORMAL_INTERCEPT;
    state->relay_bypass_active = false;
}

float calculate_vsp_out(float vsp_in, float k) {
    if (k < MIN_K_ATTEN) k = MIN_K_ATTEN;
    if (k > MAX_K_ATTEN) k = MAX_K_ATTEN;
    float vsp_out = vsp_in * k;
    if (vsp_out > 6.50f) vsp_out = 6.50f;
    if (vsp_out < 0.0f) vsp_out = 0.0f;
    return vsp_out;
}

float calculate_fg_out(float fg_in, float k, float vsp_in, bool *stall_flag) {
    *stall_flag = false;
    if (vsp_in > VSP_STALL_VOLTAGE_MIN && fg_in < FG_STALL_FREQ_HZ_MIN) {
        *stall_flag = true;
        return 0.0f; /* Active Stall Passthrough: FG_out = LOW (0 Hz) */
    }
    if (k <= 0.0f) return fg_in;
    return fg_in / k;
}

void interceptor_update(InterceptorSystemState_t *state, float vsp_in1, float vsp_in2, float fg_in1, float fg_in2, float t_evap) {
    if (!state) return;

    state->t_evap_c = t_evap;
    state->ch1.vsp_in_volts = vsp_in1;
    state->ch2.vsp_in_volts = vsp_in2;
    state->ch1.fg_in_freq_hz = fg_in1;
    state->ch2.fg_in_freq_hz = fg_in2;

    /* Check Freeze Override Threshold */
    if (t_evap < NTC_FREEZE_TEMP_C_MIN) {
        state->mode = INTERCEPTOR_MODE_FREEZE_BYPASS;
        state->relay_bypass_active = true;
        state->ch1.vsp_out_volts = vsp_in1;
        state->ch2.vsp_out_volts = vsp_in2;
        state->ch1.fg_out_freq_hz = fg_in1;
        state->ch2.fg_out_freq_hz = fg_in2;
        state->ch1.stall_detected = false;
        state->ch2.stall_detected = false;
        return;
    }

    /* Check High Load Emergency Bypass Threshold */
    if (vsp_in1 > VSP_BYPASS_VOLTAGE_MAX || vsp_in2 > VSP_BYPASS_VOLTAGE_MAX) {
        state->mode = INTERCEPTOR_MODE_HIGH_LOAD_BYPASS;
        state->relay_bypass_active = true;
        state->ch1.vsp_out_volts = vsp_in1;
        state->ch2.vsp_out_volts = vsp_in2;
        state->ch1.fg_out_freq_hz = fg_in1;
        state->ch2.fg_out_freq_hz = fg_in2;
        state->ch1.stall_detected = false;
        state->ch2.stall_detected = false;
        return;
    }

    /* Normal Intercept Operation */
    state->relay_bypass_active = false;
    float k = state->k_attenuation;

    state->ch1.vsp_out_volts = calculate_vsp_out(vsp_in1, k);
    state->ch2.vsp_out_volts = calculate_vsp_out(vsp_in2, k);

    bool stall1 = false, stall2 = false;
    state->ch1.fg_out_freq_hz = calculate_fg_out(fg_in1, k, vsp_in1, &stall1);
    state->ch2.fg_out_freq_hz = calculate_fg_out(fg_in2, k, vsp_in2, &stall2);
    state->ch1.stall_detected = stall1;
    state->ch2.stall_detected = stall2;

    if (stall1 || stall2) {
        state->mode = INTERCEPTOR_MODE_STALL_PASSTHROUGH;
    } else {
        state->mode = INTERCEPTOR_MODE_NORMAL_INTERCEPT;
    }
}
