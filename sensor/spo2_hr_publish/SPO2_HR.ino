#include <WiFi.h>
#include <PubSubClient.h>
#include <Ticker.h>
#include <Wire.h>
#include "MAX30105.h"
#include "spo2_algorithm.h"

// 设置WiFi接入信息(请根据您的WiFi信息进行修改)
const char* ssid = "test";
const char* password = "12356784";
const char* mqttServer = "192.168.193.174";
const int mqttPort = 31388;
// const char* mqttServer = "192.168.193.173";
// const int mqttPort = 31388;

Ticker ticker;
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

MAX30105 particleSensor;

#define MAX_BRIGHTNESS 255

#if defined(__AVR_ATmega328P__) || defined(__AVR_ATmega168__)
uint16_t irBuffer[100]; // infrared LED sensor data
uint16_t redBuffer[100];  // red LED sensor data
#else
uint32_t irBuffer[100]; // infrared LED sensor data
uint32_t redBuffer[100];  // red LED sensor data
#endif

int32_t bufferLength = 100; // data length
int32_t spo2; // SPO2 value
int8_t validSPO2; // indicator to show if the SPO2 calculation is valid
int32_t heartRate; // heart rate value
int8_t validHeartRate; // indicator to show if the heart rate calculation is valid

byte pulseLED = 11; // Must be on PWM pin
byte readLED = 13; // Blinks with each data read

int count; // Ticker计数用变量
int sampleCount = 0; // 计数读取的样本数

void setup()
{
  Serial.begin(9600); // initialize serial communication at 9600 bits per second:
  Wire.begin(4, 5);
  pinMode(pulseLED, OUTPUT);
  pinMode(readLED, OUTPUT);

  // 设置ESP32工作模式为无线终端模式
  WiFi.mode(WIFI_STA);
  // 连接WiFi
  connectWifi();
  // 设置MQTT服务器和端口号
  mqttClient.setServer(mqttServer, mqttPort);
  // 连接MQTT服务器
  connectMQTTServer();

  // 初始化MAX30105传感器
  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) // Use default I2C port, 400kHz speed
  {
    Serial.println(F("MAX30105 was not found. Please check wiring/power."));
    while (1);
  }

  byte ledBrightness = 60; // Options: 0=Off to 255=50mA
  byte sampleAverage = 4; // Options: 1, 2, 4, 8, 16, 32
  byte ledMode = 2; // Options: 1 = Red only, 2 = Red + IR, 3 = Red + IR + Green
  byte sampleRate = 100; // Options: 50, 100, 200, 400, 800, 1000, 1600, 3200
  int pulseWidth = 411; // Options: 69, 118, 215, 411
  int adcRange = 4096; // Options: 2048, 4096, 8192, 16384

  particleSensor.setup(ledBrightness, sampleAverage, ledMode, sampleRate, pulseWidth, adcRange); // Configure sensor with these settings

  // Ticker定时对象
  ticker.attach(1, tickerCount);
}

void loop()
{
  if (mqttClient.connected()) { // 如果开发板成功连接服务器
    // 每隔3秒钟发布一次信息
    if (count >= 3) {
      if (validHeartRate + validSPO2 >= 1) {
        pubMQTTmsg();
      } else {
        Serial.println("invalid datas");
      }
      count = 0;
    }
    // 保持心跳
    mqttClient.loop();
  } else { // 如果开发板未能成功连接服务器
    connectMQTTServer(); // 则尝试连接服务器
  }

  if (sampleCount < 100) {
    if (particleSensor.available()) { // do we have new data?
      redBuffer[sampleCount] = particleSensor.getRed();
      irBuffer[sampleCount] = particleSensor.getIR();
      particleSensor.nextSample(); // We're finished with this sample so move to next sample
      sampleCount++;
    } else {
      particleSensor.check(); // Check the sensor for new data
    }
  } else {
    maxim_heart_rate_and_oxygen_saturation(irBuffer, bufferLength, redBuffer, &spo2, &validSPO2, &heartRate, &validHeartRate);
    sampleCount = 0; // reset sample count
  }

  delay(10); // 添加一个小的延时，避免循环过于频繁
}

void tickerCount() {
  count++;
}

void connectMQTTServer() {
  // 根据ESP32的MAC地址生成客户端ID（避免与其它ESP8266的客户端ID重名）
  String clientId = "myesp32c3";

  // 连接MQTT服务器
  if (mqttClient.connect(clientId.c_str())) {
    Serial.println("MQTT Server Connected.");
  } else {
    Serial.print("MQTT Server Connect Failed. Client State:");
    Serial.println(mqttClient.state());
    delay(3000);
  }
}

// 发布信息
void pubMQTTmsg() {
  // 建立发布主题。主题名称以为前缀，后面添加设备的MAC地址。
  String topicString = "device/1234";
  char publishTopic[topicString.length() + 1];
  strcpy(publishTopic, topicString.c_str());

  // 建立发布信息。信息内容为心率和血氧数据。
  String messageString = "Heart Rate: " + String(heartRate) + " bpm, SPO2: " + String(spo2) + " %";
  char publishMsg[messageString.length() + 1];
  strcpy(publishMsg, messageString.c_str());

  // 实现ESP32向主题发布信息
  if (mqttClient.publish(publishTopic, publishMsg)) {
    Serial.println("Message Published:");
    Serial.println(publishMsg);
  } else {
    Serial.println("Message Publish Failed.");
  }
}

// ESP32连接WiFi
void connectWifi() {
  WiFi.begin(ssid, password);

  // 等待WiFi连接，成功连接后输出成功信息
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi Connected!");
  Serial.println("");
}
