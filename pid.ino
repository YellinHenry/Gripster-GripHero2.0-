#include <PID_v1.h>
#include "HX711.h"
#include <BleKeyboard.h>
//setpoint 3000
//T when begin (hold metal down)
BleKeyboard bleKeyboard;
HX711 scale;

//  adjust pins if needed
const uint8_t dataPin = 16;
const uint8_t clockPin = 17;
#define pwmPin 32
#define forward 33
#define backward 25
#define bluetoothEnablePin 19
String inputString = "";      // a String to hold incoming data
bool stringComplete = false;  // whether the string is complete
int transmitCounter = 0;
String gripState = "unknown";
const float pullingThreshold = -200;
const float releasingThreshold = 100;

//Define Variables we'll be connecting to
double Setpoint, Input, Output;

//Specify the links and initial tuning parameters
double Kp=0.4, Ki=2.5, Kd=0.005;
PID myPID(&Input, &Output, &Setpoint, Kp, Ki, Kd, DIRECT);

void setup()
{
  pinMode(pwmPin, OUTPUT);
  pinMode(forward, OUTPUT);
  pinMode(backward, OUTPUT);
  pinMode(bluetoothEnablePin, INPUT_PULLUP);
  myPID.SetOutputLimits(-255, 255);

  Serial.begin(115200);
  bleKeyboard.begin();
  scale.begin(dataPin, clockPin);
  scale.set_scale(81);       // TODO you need to calibrate this yourself.
  //  reset the scale to zero = 0
  setMotor(-255);
  delay(500);
  setMotor(0);
  delay(500);
  scale.tare();
  //initialize the variables we're linked to
  Setpoint = 0;

  //turn the PID on
  myPID.SetSampleTime(15);
  myPID.SetMode(MANUAL);
  inputString.reserve(200);
}


void loop()
{

  Input = scale.get_units(1);

  if (stringComplete) 
  {
    if(inputString[0] == 's')
    {
      Setpoint = inputString.substring(1).toFloat();
    }
    if(inputString[0] == 'p')
    {
      Kp = inputString.substring(1).toFloat();
      myPID.SetTunings(Kp, Ki, Kd, 0);
      myPID.SetMode(MANUAL);
      myPID.SetMode(AUTOMATIC);
    }
    if(inputString[0] == 'i')
    {
      Ki = inputString.substring(1).toFloat();
      myPID.SetTunings(Kp, Ki, Kd, 0);
      myPID.SetMode(MANUAL);
      myPID.SetMode(AUTOMATIC);
    }
    if(inputString[0] == 'd')
    {
      Kd = inputString.substring(1).toFloat();
      myPID.SetTunings(Kp, Ki, Kd, 0);
      myPID.SetMode(MANUAL);
      myPID.SetMode(AUTOMATIC);
    }
    if(inputString[0] == 't')
        {
          scale.set_scale(inputString.substring(1).toFloat());
        }
    if(inputString[0] == 'T')
      {
        scale.tare();
      }
    if(inputString[0] == 'm')
        {
          myPID.SetMode(MANUAL);
          Output = inputString.substring(1).toFloat();

        }
    if(inputString[0] == 'a')
        {
          myPID.SetMode(AUTOMATIC);
        }

      

    // clear the string:
    inputString = "";
    stringComplete = false;
  }
  myPID.Compute();
  setMotor (Output);
  if (Output < pullingThreshold)
  {
    //pulling
    if (bleKeyboard.isConnected() && digitalRead(bluetoothEnablePin) == false)
    {
      bleKeyboard.press('a');
    }
    gripState = "pulling";
  }
  else if (Output > releasingThreshold)
  {
    //releasing
    if (bleKeyboard.isConnected() && digitalRead(bluetoothEnablePin) == false)
    {
      bleKeyboard.release('a');
    }
    gripState = "releasing";
  }
  transmitCounter++;
  if (transmitCounter >= 25)
  {
    Serial.print(Output);
    Serial.print(",");
    Serial.print(Input);
    Serial.print(",");
    Serial.print(Kp);
    Serial.print(",");
    Serial.print(Ki);
    Serial.print(",");
    Serial.print(Kd);
    Serial.print(",");
    Serial.print(Setpoint);
    Serial.print(",");
    Serial.print(Setpoint - Input);
    Serial.print(",");
    Serial.println(gripState);
  
    transmitCounter = 0;
  }
}

void setMotor (int setPoint)
{
  if (setPoint > 255) setPoint = 255;
  if (setPoint < -255) setPoint = -255;
  int speed = abs(setPoint);
  analogWrite(pwmPin, speed);
  if (setPoint > 0)
  {
    digitalWrite(forward, HIGH);
    digitalWrite(backward, LOW);
  }
  else {
    digitalWrite(forward, LOW);
    digitalWrite(backward, HIGH);
  }
}

void serialEvent() {
  while (Serial.available()) {
    // get the new byte:
    char inChar = (char)Serial.read();
    // add it to the inputString:
    inputString += inChar;
    // if the incoming character is a newline, set a flag so the main loop can
    // do something about it:
    if (inChar == '\n') {
      stringComplete = true;
    }
  }
}
