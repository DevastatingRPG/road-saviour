#include <esp_camera.h>
#include <WiFi.h>
#include <WebServer.h>
#include <WiFiClient.h>
#include <WiFiAP.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// Motor A pins
#define MOTOR_A_IN1 1
#define MOTOR_A_IN2 2
#define MOTOR_A_PWM 5

// Motor B pins
#define MOTOR_B_IN1 3
#define MOTOR_B_IN2 4
#define MOTOR_B_PWM 6

// Buzzer Pin
#define buzzerPin 43

// const char* ssid = "Sanskruti's Galaxy S20 FE 5G";
// const char* password = "Epiphany";
const char *ssid = "Airtel_gane_0281";
const char *password = "air16031";
// const char *ssid = "XIAO_ESP32S3";
// const char *password = "password";
const uint16_t port = 8000;
const char *host = "192.168.1.8";
int take = 1;

WiFiServer server(80);

char incomingPacket[80];
WiFiClient client;
String msg;

int counter = 0;
int flag = 0;
int flag1 = 0;
int lastsignal;

bool isBuzzing = false;
unsigned long buzzStartTime = 0;
unsigned long buzzDuration = 0;

bool isMoving = false;
bool waitingAtZebra = false;
bool skipCurrentZebra = false;
int lastSignal = 0; // 0 for RED, 1 for GREEN
unsigned long lastSignalCheck = 0;
unsigned long lastServerCheck = 0;
unsigned long signalCheckInterval = 5000;
String incomingCommand = "";
unsigned long lastZebraCheckTime = 0;
bool zebra_detected = false;
bool violation = false;

void initWiFi()
{
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);
    WiFi.setTxPower(WIFI_POWER_8_5dBm);
    Serial.print("Connecting to WiFi ..");
    while (WiFi.status() != WL_CONNECTED)
    {
        Serial.print('.');
        delay(1000);
    }
    Serial.println();
    Serial.println(WiFi.localIP());
}

void moveForward()
{
    // Forward - both motors
    digitalWrite(MOTOR_A_IN1, HIGH);
    digitalWrite(MOTOR_A_IN2, LOW);
    analogWrite(MOTOR_A_PWM, 100); // Speed

    digitalWrite(MOTOR_B_IN1, LOW); // Inverted direction
    digitalWrite(MOTOR_B_IN2, HIGH);
    analogWrite(MOTOR_B_PWM, 100);
}

void moveBackward()
{
    // Backward - both motors
    digitalWrite(MOTOR_A_IN1, LOW);
    digitalWrite(MOTOR_A_IN2, HIGH);
    analogWrite(MOTOR_A_PWM, 100);

    digitalWrite(MOTOR_B_IN1, HIGH); // Inverted direction
    digitalWrite(MOTOR_B_IN2, LOW);
    analogWrite(MOTOR_B_PWM, 100);
}

void stopCar()
{
    // Stop Motor A
    digitalWrite(MOTOR_A_IN1, LOW);
    digitalWrite(MOTOR_A_IN2, LOW);
    analogWrite(MOTOR_A_PWM, 0);

    // Stop Motor B
    digitalWrite(MOTOR_B_IN1, LOW);
    digitalWrite(MOTOR_B_IN2, LOW);
    analogWrite(MOTOR_B_PWM, 0);
}

camera_fb_t *fb;

int detectSignalColor()
{

    fb = esp_camera_fb_get();
    Serial.println("image taken");

    if (!fb)
    {
        Serial.println("Camera capture failed");
        esp_camera_deinit();
        take = 1;
        cam();
        return -1;
    }

    // Create an HTTP client
    HTTPClient http;

    String serverUrl = "http://192.168.1.8:8000/process-image/";
    http.begin(serverUrl);
    http.addHeader("Content-Type", "image/jpeg");

    int httpResponseCode = http.POST(fb->buf, fb->len);

    if (httpResponseCode > 0)
    {
        Serial.printf("Image sent successfully. HTTP Response code: %d\n", httpResponseCode);
        String response = http.getString(); // Get server's response as string
        Serial.println("Server Response: " + response);

        // Parse JSON
        DynamicJsonDocument doc(1024);
        DeserializationError error = deserializeJson(doc, response);

        if (!error)
        {
            if (doc.containsKey("signal"))
            {
                lastSignal = doc["signal"];
            }
            if (doc.containsKey("zebra"))
            {
                zebra_detected = doc["zebra"];
            }
            take = 1;
        }
        else
        {
            Serial.println("❌ Failed to parse JSON");
        }
    }
    else
    {
        Serial.printf("Failed to send image. HTTP Response code: %d\n", httpResponseCode);
        take = 1;
    }

    http.end(); // End connection

    return 1;
}

void checkServerForUpdates()
{
    HTTPClient http;

    // Server URL for receiving updates
    String serverUrl = "http://192.168.1.8:8000//updates"; // Replace with your server's endpoint

    // Begin the HTTP GET request
    http.begin(serverUrl);

    // Send the GET request
    int httpResponseCode = http.GET();

    if (httpResponseCode > 0)
    {
        // If the server responds successfully
        String response = http.getString();
        Serial.printf("Server Response: %s\n", response.c_str());

        // Parse the JSON response
        DynamicJsonDocument doc(1024); // Adjust size as needed
        DeserializationError error = deserializeJson(doc, response);

        if (error)
        {
            Serial.print("JSON parsing failed: ");
            Serial.println(error.c_str());
            return;
        }

        // Extract values from JSON
        int lastsignal = doc["signal"];    // Assuming the key is "signal"
        int zebra_detected = doc["zebra"]; // Assuming the key is "zebra"
        take = 1;
    }
    else
    {
        // If the server request fails
        // Serial.printf("Failed to get updates. HTTP Response code: %d\n", httpResponseCode);
    }

    // End the HTTP connection
    http.end();
}

void startBuzzing(bool signal, bool skipping = false)
{
    if (!signal && skipping)
        buzzDuration = 4000;
    else if (!signal)
        buzzDuration = 5000;
    else if (signal)
        buzzDuration = 2000;
    else
        buzzDuration = 0;

    if (buzzDuration > 0)
    {
        digitalWrite(buzzerPin, HIGH);
        buzzStartTime = millis();
        isBuzzing = true;
    }
}

void updateBuzzer()
{
    if (isBuzzing && millis() - buzzStartTime >= buzzDuration)
    {
        digitalWrite(buzzerPin, LOW);
        violation = false;
        isBuzzing = false;
    }
}

void sendViolationStart(int violationType = 1, String location = "Pune")
{
    HTTPClient http;
    String serverUrl = "http://192.168.1.8:8000/violation-start/";

    // Begin the HTTP request
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");

    // Create the JSON payload
    String jsonPayload = "{\"violation_type\": " + String(violationType) + ", \"location\": \"" + location + "\"}";

    // Send the POST request
    int httpResponseCode = http.POST(jsonPayload);

    // Check the response
    if (httpResponseCode > 0)
    {
        Serial.printf("Violation start sent successfully. HTTP Response code: %d\n", httpResponseCode);
    }
    else
    {
        Serial.printf("Failed to send violation start. HTTP Response code: %d\n", httpResponseCode);
    }

    // End the HTTP connection
    http.end();
}

unsigned long tame = millis();

void sendViolationEnd(int violationType = 1)
{
    HTTPClient http;
    String serverUrl = "http://192.168.1.8:8000/violation-end/";

    // Begin the HTTP request
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");

    // Create the JSON payload
    String jsonPayload = "{\"violation_type\": " + String(violationType) + "}";

    // Send the POST request
    int httpResponseCode = http.POST(jsonPayload);

    // Check the response
    if (httpResponseCode > 0)
    {
        Serial.printf("Violation end sent successfully. HTTP Response code: %d\n", httpResponseCode);
    }
    else
    {
        Serial.printf("Failed to send violation end. HTTP Response code: %d\n", httpResponseCode);
    }

    // End the HTTP connection
    http.end();
}

void sendImageToServer(camera_fb_t *fb)
{
    HTTPClient http;
    String serverUrl = "http://192.168.1.8:8000/upload-image/";

    // Begin the HTTP request
    http.begin(serverUrl);
    http.addHeader("Content-Type", "image/jpeg");

    // Send the POST request with the image data
    int httpResponseCode = http.POST(fb->buf, fb->len);

    // Check the response
    if (httpResponseCode > 0)
    {
        Serial.printf("Image sent successfully. HTTP Response code: %d\n", httpResponseCode);
    }
    else
    {
        Serial.printf("Failed to send image. HTTP Response code: %d\n", httpResponseCode);
    }

    // End the HTTP connection
    http.end();
}

String name = "Vijit";

void registerName(String name)
{
    HTTPClient http;
    String serverUrl = "http://192.168.1.8:8002/register-name/";

    // Begin the HTTP request
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");

    // Create the JSON payload
    String jsonPayload = "{\"name\": \"" + name + "\"}";

    // Send the POST request
    int httpResponseCode = http.POST(jsonPayload);

    // Check the response
    if (httpResponseCode > 0)
    {
        Serial.printf("Name registered successfully. HTTP Response code: %d\n", httpResponseCode);
    }
    else
    {
        Serial.printf("Failed to register name. HTTP Response code: %d\n", httpResponseCode);
    }

    // End the HTTP connection
    http.end();
}

// OV2640 camera module pin mapping for Seeed XIAO ESP32S3
#define PWDN_GPIO_NUM -1
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 10
#define SIOD_GPIO_NUM 40
#define SIOC_GPIO_NUM 39

#define Y9_GPIO_NUM 48
#define Y8_GPIO_NUM 11
#define Y7_GPIO_NUM 12
#define Y6_GPIO_NUM 14
#define Y5_GPIO_NUM 16
#define Y4_GPIO_NUM 18
#define Y3_GPIO_NUM 17
#define Y2_GPIO_NUM 15
#define VSYNC_GPIO_NUM 38
#define HREF_GPIO_NUM 47
#define PCLK_GPIO_NUM 13

bool backward = false;

void setup()
{
    Serial.begin(115200);

    // Set all pins as OUTPUT
    pinMode(MOTOR_A_IN1, OUTPUT);
    pinMode(MOTOR_A_IN2, OUTPUT);
    pinMode(MOTOR_A_PWM, OUTPUT);

    pinMode(MOTOR_B_IN1, OUTPUT);
    pinMode(MOTOR_B_IN2, OUTPUT);
    pinMode(MOTOR_B_PWM, OUTPUT);

    // Initially stop both motors
    stopCar();

    // Buzzer
    pinMode(buzzerPin, OUTPUT);

    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sscb_sda = SIOD_GPIO_NUM;
    config.pin_sscb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;

    config.pixel_format = PIXFORMAT_JPEG;
    config.frame_size = FRAMESIZE_QQVGA; // very small
    config.jpeg_quality = 15;            // more compression
    config.fb_count = 1;                 // fewer buffers = less RAM

    Serial.println("Initializing camera...");
    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK)
    {
        Serial.printf("Camera init failed with error 0x%x\n", err);
        if (err == ESP_ERR_NOT_FOUND)
            Serial.println("Camera not found. Check pin connections.");
        else if (err == ESP_ERR_INVALID_ARG)
            Serial.println("Invalid arguments. Check config.");
        else if (err == ESP_ERR_INVALID_STATE)
            Serial.println("Camera already initialized?");
        return;
    }

    Serial.println("Camera initialized");

    initWiFi();

    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
    config.fb_location = CAMERA_FB_IN_PSRAM;
    WiFi.softAP(ssid);
    IPAddress myIP = WiFi.softAPIP();
    Serial.print("AP IP address: ");
    Serial.println(myIP);
    server.begin();
}

void cam()
{
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sscb_sda = SIOD_GPIO_NUM;
    config.pin_sscb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;

    config.pixel_format = PIXFORMAT_JPEG;
    config.frame_size = FRAMESIZE_QQVGA; // very small
    config.jpeg_quality = 15;            // more compression
    config.fb_count = 1;                 // fewer buffers = less RAM

    Serial.println("Initializing camera...");
    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK)
    {
        Serial.printf("Camera init failed with error 0x%x\n", err);
        if (err == ESP_ERR_NOT_FOUND)
            Serial.println("Camera not found. Check pin connections.");
        else if (err == ESP_ERR_INVALID_ARG)
            Serial.println("Invalid arguments. Check config.");
        else if (err == ESP_ERR_INVALID_STATE)
            Serial.println("Camera already initialized?");
        return;
    }

    Serial.println("Camera initialized");
}
String value;
void loop()
{

    WiFiClient client = server.available(); // listen for incoming clients

    if (client)
    {                                  // if you get a client,
        Serial.println("New Client."); // print a message out the serial port
        String currentLine = "";       // make a String to hold incoming data from the client
        // while (client.connected()) {    // loop while the client's connected
        //   if (client.available()) {
        //     char c = client.read();  // read a byte, then
        //     Serial.write(c);
        //     if (value == "0") {
        //       stopCar();
        //       isMoving = false;
        //     }
        //     if (value == "1") {
        //       if (!isMoving && waitingAtZebra) {
        //         moveForward();
        //         skipCurrentZebra = true;
        //         waitingAtZebra = false;
        //         if (!lastSignal) {
        //           startBuzzing(lastSignal, true);
        //           violation = true;
        //         }
        //       }
        //       isMoving = true;
        //     }
        //   }
        // }

        String request = client.readStringUntil('\r');
        Serial.println("Request: " + request);
        client.flush();

        if (request.indexOf("/move=1") != -1)
        {
            // digitalWrite(ledPin, HIGH);
            if (!isMoving && waitingAtZebra)
            {
                skipCurrentZebra = true;
                waitingAtZebra = false;
                if (!lastSignal)
                {
                    startBuzzing(lastSignal, true);
                    violation = true;
                }
            }
            isMoving = true;
            backward = false;
        }
        else if (request.indexOf("/move=0") != -1)
        {
            // digitalWrite(ledPin, LOW);
            stopCar();
            isMoving = false;
            backward = false;
        }
        else if (request.indexOf("/move=2") != -1)
        {
            backward = true;
            isMoving = true;
        }
        else if (request.indexOf("/signal=0") != -1)
        {
            lastSignal = 0;
        }
        else if (request.indexOf("/signal=1") != -1)
        {
            lastSignal = 1;
        }
        else if (request.indexOf("/zebra=0") != -1)
        {
            zebra_detected = 0;
        }
        else if (request.indexOf("/zebra=1") != -1)
        {
            zebra_detected = 1;
        }
        take = 1;
        client.println("HTTP/1.1 200 OK");
        client.println("Content-Type: text/plain");
        client.println("Access-Control-Allow-Origin: *"); // Allow all origins
        client.println("Access-Control-Allow-Methods: GET, POST, OPTIONS");
        client.println("Access-Control-Allow-Headers: *");
        client.println("Connection: close");
        client.println();
        client.println("Command received");
    }

    unsigned long currentMillis = millis();
    bool skipping = false;
    // 1. Background signal detection every 2.5 sec
    if (currentMillis - lastSignalCheck >= duration && take)
    {
        // lastSignal = detectSignalColor();
        take = 0;
        int l = detectSignalColor();
        lastSignalCheck = currentMillis;
        Serial.println("Updated Signal Detected: " + lastSignal);
    }

    // if (currentMillis - lastServerCheck >= 500) {
    //   checkServerForUpdates();
    //   lastServerCheck = currentMillis;
    // }

    if (violation && currentMillis - tame >= 750)
    {
        sendImageToServer(fb);
        sendViolationStart();
        sendViolationEnd();
        tame = millis();
    }
    // 3. Update Buzzer
    updateBuzzer();

    if (isMoving)
    {
        if (zebra_detected && !skipCurrentZebra)
        {
            stopCar();
            Serial.println("Zebra Crossing Detected. Stopping...");
            isMoving = false;
            waitingAtZebra = true;
            startBuzzing(lastSignal);
        }
        else
        {
            if (!backward)
                moveForward();
            else
                moveBackward();
            // tone(buzzerPin, 1000, 100);
            Serial.println("Moving for");
        }
    }
    //
    // 5. Reset zebra crossing skip when it is no longer visible
    if (skipCurrentZebra && !zebra_detected)
    {
        skipCurrentZebra = false;
    }

    // delay(100);
}