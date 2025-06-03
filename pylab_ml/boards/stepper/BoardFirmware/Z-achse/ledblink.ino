#include "ledblink.h"

unsigned long led_time,led_time_target;


void led_setup() {
    led_time_target=LED_TIME_OFF;
    led_time=millis();
}


void led_blink() {
    if ((millis()-led_time)>led_time_target){
        //Serial.println(millis());
        led_time=millis();     
        if (led_time_target==LED_TIME_ON) {
            led_time_target=LED_TIME_OFF;
            if (led_mode == LED_STATUS) LED_OFF;
        }else {
            led_time_target=LED_TIME_ON;
            if (led_mode == LED_STATUS){LED_CONFIG; LED_ON;}
        }
    }
}
