// Available Functions for Z-Achse QDB-Messplatz
// Author : C. Jung
// Version: 1.0#
// Date: 25.05.2020
//
#include <AccelStepper.h>
//   info about stepper:  https://www.pjrc.com/teensy/td_libs_AccelStepper.html


// function decklaration for mixing c-file with *.ino
extern "C" void step_reset();
extern "C" int  step_get();       
extern "C" void step_move(int distance);
extern "C" void step_moveto(int position);
extern "C" int  step_getenable();
extern "C" void step_setenable(int val);
extern "C" void step_setspeed(int value);
extern "C" int  step_getacceleration();
extern "C" void step_setacceleration(int value);
extern "C" int  step_getspeed();
extern "C" int step_running();

//AccelStepper Xaxis(1, 2, 5); // pin 2 = step, pin 5 = direction
//AccelStepper Yaxis(1, 3, 6); // pin 3 = step, pin 6 = direction
AccelStepper Zaxis(1, 4, 7);   // pin 4 = step, pin 7 = direction

#define STEPPER_EN_PIN  8      // pin 8 = enable current
#define STEPPER_ON              digitalWrite(STEPPER_EN_PIN,LOW)    //pin 8 = not enable
#define STEPPER_OFF             digitalWrite(STEPPER_EN_PIN,HIGH)
#define STEPPER_MAXSPEED 16*200*2  // 2 U/s = 120 U/min 
#define STEPPER_ACCELERATION 4000
#define STEPPER_DIR   1      

int step_on;
int step_speed;
int step_acceleration;


void step_reset(){
     Zaxis.setCurrentPosition(0);
     step_setenable(0);
     step_setspeed(STEPPER_MAXSPEED);
     step_setacceleration(STEPPER_ACCELERATION);     
}

// set/get position:
int step_get() {
   int value;
   value=STEPPER_DIR*Zaxis.currentPosition();
   return value;
}

void step_move(int distance) {
    Zaxis.move(STEPPER_DIR*distance);  
} 

void step_moveto(int position){
    Zaxis.moveTo(STEPPER_DIR*position);  
} 

// set/get speed:
int step_getspeed(){
    return step_speed;
}

void step_setspeed(int value){
    Zaxis.setMaxSpeed(value);
    step_speed=value;
}


// set/get acceleration:
int step_getacceleration(){
    return step_acceleration;
}

void step_setacceleration(int value){
    Zaxis.setAcceleration(value);
    step_acceleration=value;
}


// set/get enable:
int step_getenable() {
    return step_on;
}

void step_setenable(int val){
    if (val==0) {
        STEPPER_OFF;
        step_on=0;
    }else {
        STEPPER_ON;
        step_on=1;
    }
}

int step_running(){
    int value;
    value=Zaxis.distanceToGo();
    if (value!=0)value=1;
    return value;
}
// _________________________

void stepper_setup(){       // init Stepper motors
    pinMode(STEPPER_EN_PIN,OUTPUT);
    step_setenable(0);
    step_setspeed(STEPPER_MAXSPEED);
    step_setacceleration(STEPPER_ACCELERATION);
}


void stepper_loop(){      // This must be called repetitively to make the motor move. 
   Zaxis.run();
}
