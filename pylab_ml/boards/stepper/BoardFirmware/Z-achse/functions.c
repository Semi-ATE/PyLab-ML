#include "functions.h"
//#include "tcl_interpreter.h"

void print_fw_version(void)
{
   //Print Program Information
   printLine ("\r\n\r\nTeensy 3.2 (Cortex-M4) Stepper Board");
   prints ("Version 0.0.1 (c) 2020 Micronas CJ, ");
   prints (__DATE__ );prints (" ");  
   printLine (__TIME__);
   printLine ("Type ? for Help");
}



void print_help(void){  
    printLine ("-----------------------------------------------");
    printLine ("Stepper motor control:");  
    printLine ("200*16 steps = 1 rotation");  
    printLine ("   reset");
    printLine ("       reset Teensy interface status, set current position to 0, disable current");  
    printLine ("   step move <value> ");
    printLine ("       stepper motor makes <value> steps += clockwise, -=counterclockwise");
    printLine ("   step get"); 
    printLine ("       get current position, (0=reset value, or value after POR)");   
    printLine ("   step_setspeed <value>");
    printLine ("       set maximum speed =steps/s");
    printLine ("   step getspeed ");
    printLine ("       get maximum speed =steps/s");
    printLine ("   step setenable <value>");
    printLine ("       <value>=1 : enable motor current, <value>=0: disable motor current");
    printLine ("   step getenable ");
    printLine ("       get =1 motor current is enabled, 0= motor current is disabled");
    printLine ("   step running ");
    printLine ("       get 0, if reached its final position, otherwise 1");    
    printLine (" ");    
    printLine ("   v?");
    printLine ("       Firmware Version");    
    printLine ("   ?");
    printLine ("       Help");    
   
    printLine ("-----------------------------------------------");   
}
