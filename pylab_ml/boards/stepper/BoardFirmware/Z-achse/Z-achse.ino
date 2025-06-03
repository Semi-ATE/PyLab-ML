// Firmware for Z-Achse QDB-Messplatz
// Author : C. Jung
// Version: 1.0#
// Date: 25.05.2020
//

#include <SPI.h>
#include "tcl_interpreter.h"
#include "functions.h"
#include "ledblink.h"

extern struct tcl tcl;
enum LED_MODES led_mode;

void setup() {

    
    led_mode = LED_STATUS;
    
    while(!Serial) {}                //wait for serial port to connect. Needed for native USB port only
    Serial.begin(120000);            // USB is always 12MBit/sec

    stepper_setup();  
    tcl_init(&tcl);
    // turn on the LED
    LED_CONFIG;
    LED_ON;
    delay (500);
    LED_OFF;
    led_setup();
    print_fw_version();
}

void loop() {
   static int16_t n;  
   
   n = check_recv();
   if (n != 0) {
       if (led_mode == LED_STATUS) {LED_CONFIG; LED_ON;}
       parse_and_execute_command(n);
       if (led_mode == LED_STATUS) {LED_OFF;}
   }
   stepper_loop();
   led_blink();
}
