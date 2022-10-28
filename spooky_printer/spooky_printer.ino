#include "Adafruit_Thermal.h"
#include <WiFiNINA.h>

#define TIMEOUT_MS 3000
#define MESSAGE_BUFFER_SIZE 1024

char ssid[] = "Tomorrow's Flowers";        // your network SSID (name)
char pass[] = "WiFi Password goes here";
int status = WL_IDLE_STATUS;  

WiFiClient client;
WiFiServer server(5000);

Adafruit_Thermal printer(&Serial1); 

char message_buffer[MESSAGE_BUFFER_SIZE];

void setup() {
  Serial.begin(9600);
  Serial.println("START");
  Serial1.begin(19200);
  printer.begin(); 

  status = WiFi.begin(ssid, pass);
  while (status != WL_CONNECTED) {
    delay(3000);
    status = WiFi.begin(ssid, pass);
  }
  
  server.begin();
  IPAddress myAddress = WiFi.localIP();
  Serial.println(myAddress);
  printer.println(myAddress);
  printer.println("");
}

void loop() {
  client = server.available();
  if (!client) {
    return;
  }
  if (!client.connected()) {
    return;
  }
  printer.wake();
  read_instructions();
  client.stop();
  printer.sleep();
}

void read_instructions() {
  while (true) {
    char instruction = wait_for_data();
    if (instruction == 'E') {
      Serial.println(">>> Instructions End");
      return;
    }
    handle_instruction(instruction);
  }
}

int read_int() {
  char buffer[6];
  read_until(buffer, ' ', 6);
  return atoi(buffer);
}

void read_data(uint8_t* buffer, uint16_t size) {
  for(int i = 0; i < size; ++i) {
    buffer[i] = (uint8_t) wait_for_data();
  }
}

void print_image() {
  int width = read_int();
  int height = read_int();
  uint16_t data_size = width * height / 8;
  uint8_t image_data[data_size];
  read_data(image_data, data_size);
  printer.printBitmap(width, height, image_data);
}

void print_line() {
  read_line(message_buffer, MESSAGE_BUFFER_SIZE);
  Serial.println(message_buffer);
  printer.println(message_buffer);
}

void handle_instruction(char instruction) {
  Serial.print(">>> ");
  switch (instruction) {
    case 'B':
      Serial.println("Bold ON");
      printer.boldOn();
      break;
    case 'b':
      Serial.println("Bold OFF");
      printer.boldOff();
      break;
    case 'L':
      Serial.println("Justify L");
      printer.justify('L');
      break;
    case 'C':
      Serial.println("Justify C");
      printer.justify('C');
      break;
    case 'R':
      Serial.println("Justify R");
      printer.justify('R');
      break;
    case 's':
      Serial.println("Size S");
      printer.setSize('S');
      break;
    case 'm':
      Serial.println("Size M");
      printer.setSize('M');
      break;
    case 'l':
      Serial.println("Size L");
      printer.setSize('L');
      break;
    case 'I':
      Serial.println("Inverse ON");
      printer.inverseOn();
      break;
    case 'i':
      Serial.println("Inverse OFF");
      printer.inverseOff();
      break;
    case 'U':
      Serial.println("Underline ON");
      printer.underlineOn();
      break;
    case 'u':
      Serial.println("Underline OFF");
      printer.underlineOff();
      break;
    case 'D':
      Serial.println("Double Height ON");
      printer.doubleHeightOn();
      break;
    case 'd':
      Serial.println("Double Height OFF");
      printer.doubleHeightOff();
      break;
    case ';':
      Serial.println("Print Line");
      print_line();
      break;
    case ':':
      Serial.println("Print Image");
      print_image();
      break;
    default:
      Serial.print("Unknown instruction: ");
      break;
  }
}

char wait_for_data() {
  peek_for_data();
  return client.read();
}

char peek_for_data() {
  unsigned long start = millis();
  while (!client.available()) {
    unsigned long spent = millis() - start;
    if (spent > TIMEOUT_MS) {
      return 0;
    }
    delay(10);
  }
  return client.peek();
}

bool seek(char seek_c) {
  while (true) {
    char c = wait_for_data();
    if (c == 0) {
      return false;
    }
    if (c == seek_c) {
      return true;
    }    
  }
}

bool read_until(char* buffer, char end, uint16_t size) {
  uint16_t read = 0;
  while (read < size) {
    buffer[0] = wait_for_data();
    if (buffer[0] == 0) {
      Serial.println("ru: no data");
      return false;
    }
    read++;
    if (buffer[0] == end) {
      buffer[0] = 0;
      return true;
    }
    buffer++;
  }
  Serial.println("ru: limit");
  return false;
}

bool read_line(char* buffer, uint16_t size) {
  return read_until(buffer, '\n', size);
}
