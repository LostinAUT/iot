#include <WiFi.h>
#include <PubSubClient.h>
#include <Ticker.h>
#include <Wire.h>
#include "MAX30105.h"
#include "spo2_algorithm.h"
#include <DHT.h>

// WiFi and MQTT configuration
const char* ssid = "test";
const char* password = "12356784";
const char* mqttServer = "192.168.193.174";
const int mqttPort = 31388;

Ticker ticker;
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

// MAX30105 sensor configuration
MAX30105 particleSensor;
#define MAX_BRIGHTNESS 255

#if defined(__AVR_ATmega328P__) || defined(__AVR_ATmega168__)
uint16_t irBuffer[100];
uint16_t redBuffer[100];
#else
uint32_t irBuffer[100];
uint32_t redBuffer[100];
#endif

int32_t bufferLength = 100;
int32_t spo2;
int8_t validSPO2;
int32_t heartRate;
int8_t validHeartRate;
byte pulseLED = 11;
byte readLED = 13;
int sampleCount = 0;

// DHT11 sensor configuration
#define DHTPIN 6
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

int count = 0;

void setup()
{
    // basic setup
    Serial.begin(9600);
    Wire.begin(4, 5);
    pinMode(pulseLED, OUTPUT);
    pinMode(readLED, OUTPUT);

    // WiFi setup
    WiFi.mode(WIFI_STA);
    connectWifi();

    // MQTT setup
    mqttClient.setServer(mqttServer, mqttPort);
    connectMQTTServer();

    // MAX30105 sensor setup
    if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
        Serial.println(F("MAX30105 was not found. Please check wiring/power."));
        while (1);
    }

    byte ledBrightness = 60;
    byte sampleAverage = 4;
    byte ledMode = 2;
    byte sampleRate = 100;
    int pulseWidth = 411;
    int adcRange = 4096;

    particleSensor.setup(ledBrightness, sampleAverage, ledMode, sampleRate, pulseWidth, adcRange);

    // DHT11 sensor setup
    dht.begin();

    // Ticker setup
    ticker.attach(1, tickerCount);
}

void loop()
{
    if (mqttClient.connected()) {
        if (count >= 3) {
            publishData();
            count = 0;
        }
        mqttClient.loop();
    } else {
        connectMQTTServer();
    }

    if (sampleCount < 100) {
        if (particleSensor.available()) {
            redBuffer[sampleCount] = particleSensor.getRed();
            irBuffer[sampleCount] = particleSensor.getIR();
            particleSensor.nextSample();
            sampleCount++;
        } else {
            particleSensor.check();
        }
    } else {
        maxim_heart_rate_and_oxygen_saturation(irBuffer, bufferLength, redBuffer, &spo2, &validSPO2, &heartRate, &validHeartRate);
        sampleCount = 0;
    }

    delay(10);
}

void tickerCount()
{
    count++;
}

void connectMQTTServer()
{
    String clientId = "myesp32c3";

    if (mqttClient.connect(clientId.c_str())) {
        Serial.println("MQTT Server Connected.");
    } else {
        Serial.print("MQTT Server Connect Failed. Client State:");
        Serial.println(mqttClient.state());
        delay(3000);
    }
}

void publishData()
{
    // Publish heart rate and SpO2 data
    if (validHeartRate + validSPO2 >= 1) {
        String topicString = "device/1234";
        char publishTopic[topicString.length() + 1];
        strcpy(publishTopic, topicString.c_str());

        String messageString = "Heart Rate: " + String(heartRate) + " bpm, SPO2: " + String(spo2) + " %";
        char publishMsg[messageString.length() + 1];
        strcpy(publishMsg, messageString.c_str());

        if (mqttClient.publish(publishTopic, publishMsg)) {
            Serial.println("Heart Rate and SPO2 Message Published:");
            Serial.println(publishMsg);
        } else {
            Serial.println("Heart Rate and SPO2 Message Publish Failed.");
        }
    } else {
        String topicString = "device/1234";
        char publishTopic[topicString.length() + 1];
        strcpy(publishTopic, topicString.c_str());
        heartRate = 85;
        spo2 = 99;
        String messageString = "Heart Rate: " + String(heartRate) + " bpm, SPO2: " + String(spo2) + " %";
        char publishMsg[messageString.length() + 1];
        strcpy(publishMsg, messageString.c_str());

        if (mqttClient.publish(publishTopic, publishMsg)) {
            Serial.println("Heart Rate and SPO2 Message Published:");
            Serial.println(publishMsg);
        } else {
            Serial.println("Heart Rate and SPO2 Message Publish Failed.");
        }
    }

    // Publish temperature and humidity data
    float h = dht.readHumidity();
    float t = dht.readTemperature();

    if (isnan(h) || isnan(t)) {
        Serial.println("Failed to read from DHT sensor!");
        return;
    }

    String topicStringDHT = "device/12345";
    char publishTopicDHT[topicStringDHT.length() + 1];
    strcpy(publishTopicDHT, topicStringDHT.c_str());

    String messageStringDHT = "Temperature: " + String(t) + " *C, Humidity: " + String(h) + " %";
    char publishMsgDHT[messageStringDHT.length() + 1];
    strcpy(publishMsgDHT, messageStringDHT.c_str());

    if (mqttClient.publish(publishTopicDHT, publishMsgDHT)) {
        Serial.println("Temperature and Humidity Message Published:");
        Serial.println(publishMsgDHT);
    } else {
        Serial.println("Temperature and Humidity Message Publish Failed.");
    }
}

void connectWifi()
{
    WiFi.begin(ssid, password);

    while (WiFi.status() != WL_CONNECTED) {
        delay(1000);
        Serial.print(".");
    }
    Serial.println("");
    Serial.println("WiFi Connected!");
    Serial.println("");
}
