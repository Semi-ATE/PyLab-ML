#include "functions.h"
//#include "tcl_interpreter.h"

//https://isocpp.org/wiki/faq/mixing-c-and-cpp
//

extern void printLine(const char *string);



void print_fw_version(void)
{
   //Print Program Information
   printLine ("\r\n\r\nTeensy 3.2 (Cortex-M4) Stepper Board");
   printLine ("Version 0.0.0 (c) 2020 Micronas CJ");
   printLine (__DATE__);
   printLine (__TIME__);
   printLine ("Type ? for Help");
}



void print_help(void){  
    printLine ("-----------------------------------------------");
    printLine ("   reset");
    printLine ("       reset Teensy interface status");    
    printLine ("   v?");
    printLine ("       Firmware Version");    
    printLine ("   ?");
    printLine ("       Help");    
    printLine ("-----------------------------------------------");   
}

/*
void stepmove(cnt) {
    //Zaxis.moveTo(targetPosition); 
    //Zaxis.move(distance); 
    //Zaxis.currentPosition(); 
    //Zaxis.move(distance);
    printLine ("stepmove");  
} 
*/
