#include <WiFi.h>
#include <PubSubClient.h>
#include <Ticker.h>
#include <DHT.h>  // 引入DHT库

// 设置wifi接入信息(请根据您的WiFi信息进行修改)
const char* ssid = "test";
const char* password = "12356784";
const char* mqttServer = "192.168.193.173";

// DHT11 相关定义
#define DHTPIN 4     // 定义DHT11连接的引脚
#define DHTTYPE DHT11  // 定义传感器类型为DHT11
DHT dht(DHTPIN, DHTTYPE);

Ticker ticker;
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

int count;    // Ticker计数用变量

void setup() {
  Serial.begin(9600);
  
  //设置ESP8266工作模式为无线终端模式
  WiFi.mode(WIFI_STA);
  
  // 连接WiFi
  connectWifi();
  
  // 设置MQTT服务器和端口号
  mqttClient.setServer(mqttServer, 31388);
 
  // 连接MQTT服务器
  connectMQTTServer();
 
  // 初始化DHT传感器
  dht.begin();

  // Ticker定时对象
  ticker.attach(1, tickerCount);  
}

void loop() { 
  if (mqttClient.connected()) { // 如果开发板成功连接服务器
    // 每隔3秒钟发布一次信息
    if (count >= 3){
      pubMQTTmsg();
      count = 0;
    }    
    // 保持心跳
    mqttClient.loop();
  } else {                  // 如果开发板未能成功连接服务器
    connectMQTTServer();    // 则尝试连接服务器
  }
}

void tickerCount(){
  count++;
}

void connectMQTTServer(){
  // 根据ESP8266的MAC地址生成客户端ID（避免与其它ESP8266的客户端ID重名）
  String clientId = "myesp8266";

  // 连接MQTT服务器
  if (mqttClient.connect(clientId.c_str())) { 
    Serial.println("MQTT Server Connected.");
    Serial.println("Server Address: ");
    Serial.println(mqttServer);
    Serial.println("ClientId:");
    Serial.println(clientId);
  } else {
    Serial.print("MQTT Server Connect Failed. Client State:");
    Serial.println(mqttClient.state());
    delay(3000);
  }   
}

// 发布信息
void pubMQTTmsg(){
  // 读取DHT传感器的数据
  float h = dht.readHumidity();
  float t = dht.readTemperature();

  // 检查是否读取失败
  if (isnan(h) || isnan(t)) {
    Serial.println("Failed to read from DHT sensor!");
    return;
  }

  // 建立发布主题。主题名称以为前缀，后面添加设备的MAC地址。
  String topicString = "device/12345";
  char publishTopic[topicString.length() + 1];  
  strcpy(publishTopic, topicString.c_str());

  // 建立发布信息。信息内容为温湿度数据。
  String messageString = "Temperature: " + String(t) + " *C, Humidity: " + String(h) + " %"; 
  char publishMsg[messageString.length() + 1];   
  strcpy(publishMsg, messageString.c_str());

  // 实现ESP8266向主题发布信息
  if(mqttClient.publish(publishTopic, publishMsg)){
    Serial.println("Publish Topic:");Serial.println(publishTopic);
    Serial.println("Publish message:");Serial.println(publishMsg);    
  } else {
    Serial.println("Message Publish Failed."); 
  }
}

// ESP8266连接wifi
void connectWifi(){

  WiFi.begin(ssid, password);

  //等待WiFi连接,成功连接后输出成功信息
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi Connected!");  
  Serial.println(""); 
}
