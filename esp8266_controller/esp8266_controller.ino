#include <ESP8266WiFi.h>
#include <WiFiUdp.h>

const char* ssid = "RobotCar_AP";
const char* password = "robotpassword";

WiFiUDP Udp;
unsigned int localUdpPort = 4210;
char incomingPacket[255];

const int IN1 = D1;
const int IN2 = D2;
const int IN3 = D3;
const int IN4 = D4;

void setup() {
  Serial.begin(115200);
  
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);

  WiFi.softAP(ssid, password);
  
  Udp.begin(localUdpPort);
  Serial.println();
  Serial.println(WiFi.softAPIP());
}

void loop() {
  int packetSize = Udp.parsePacket();
  if (packetSize) {
    int len = Udp.read(incomingPacket, 255);
    if (len > 0) {
      incomingPacket[len] = '\0';
    }
    
    String command = String(incomingPacket);
    command.trim();
    
    if (command == "TURN") {
      digitalWrite(IN1, HIGH);
      digitalWrite(IN2, LOW);
      digitalWrite(IN3, LOW);
      digitalWrite(IN4, HIGH);
    } 
    else if (command == "STOP") {
      digitalWrite(IN1, LOW);
      digitalWrite(IN2, LOW);
      digitalWrite(IN3, LOW);
      digitalWrite(IN4, LOW);
    }
  }
}
