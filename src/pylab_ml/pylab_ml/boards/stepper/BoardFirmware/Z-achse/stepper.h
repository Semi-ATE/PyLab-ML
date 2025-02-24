#ifndef _STEPPER_H
#define _STEPPER_H

void step_reset();
int  step_get();
void step_move(int distance);
void step_moveto(int position);
int  step_getenable();
void step_setenable(int val);
void step_setspeed(int value);
int  step_getspeed();
void step_setacceleration(int value);
int  step_getacceleration();
int step_running();

#endif // _STEPPER_H
