/* UART asynchronous example, that uses separate RX and TX tasks

   This example code is in the Public Domain (or CC0 licensed, at your option.)

   Unless required by applicable law or agreed to in writing, this
   software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
   CONDITIONS OF ANY KIND, either express or implied.
*/
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_system.h"
#include "esp_log.h"
#include "driver/gpio.h"
#include "driver/uart.h"
#include "soc/uart_struct.h"
#include "string.h"
#include "send.c"

static const int RX_BUF_SIZE = 1024;

#define TXD_PIN (GPIO_NUM_47)
#define RXD_PIN (GPIO_NUM_48)

uint8_t GPS_data[600];
uint8_t coordinate_size = 11;
uint16_t Latitude[11];  //Latitude 纬度, Data format: ddmm.mmmm;     dd.ddddd = dd + mm.mmmm/60
uint16_t Longitude[12]; //Longitude 经度, Data format: dddmm.mmmm;   ddd.ddddd = dd + mm.mmmm/60
uint16_t N_S[1], E_W[1];

uint16_t *latitude = Latitude;
uint16_t *longitude = Longitude;
uint16_t *n_s = &N_S[0];
uint16_t *e_w = &E_W[0];

bool GPS_State(uint16_t data_point);
void get_coordinate(void);
uint16_t point = 0;

// 配置 UART 参数并安装 UART 驱动程序
void init_GPS()
{
    // 设置 UART 的波特率、数据位、校验位、停止位等参数
    const uart_config_t uart_config = {
        .baud_rate = 9600,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT};
        
    // 配置 UART 参数
    uart_param_config(UART_NUM_2, &uart_config);
    // 设置 UART 的引脚配置
    ESP_ERROR_CHECK(uart_set_pin(UART_NUM_2, TXD_PIN, RXD_PIN, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));
    // 安装 UART 驱动程序，并获取队列
    ESP_ERROR_CHECK(uart_driver_install(UART_NUM_2, RX_BUF_SIZE * 2, 0, 0, NULL, 0));
}

// 发送数据到 UART
int sendData(const char *logName, const char *data)
{
    const int len = strlen(data);
    const int txBytes = uart_write_bytes(UART_NUM_2, data, len);
    ESP_LOGI(logName, "Wrote %d bytes", txBytes);
    return txBytes;
}


// 从 UART 接收GPS数据，并判断是否接收到有效的GPS数据
// 如果接收到有效数据，则调用 get_coordinate()函数提取并打印经纬度信息
static void rx_task()
{
    static const char *RX_TASK_TAG = "RX_TASK";
    esp_log_level_set(RX_TASK_TAG, ESP_LOG_INFO);
    while (1)
    {
        // 从UART_NUM_2串口读取GPS数据
        const int rxBytes = uart_read_bytes(UART_NUM_2, GPS_data, RX_BUF_SIZE, 500 / portTICK_PERIOD_MS);
        // 成功读取到了数据(连接到卫星)
        if (rxBytes > 0)
        {
            // SendLocation("126.0", "N", "38.0", "E");
                // break;

            get_coordinate();
            break;
            // ESP_LOGI(RX_TASK_TAG, "Read %d bytes: '%s'", rxBytes, GPS_data);
            // 提取经纬度信息
            if (GPS_State(point))
            {
                
                break;
            }
        }
        // 将 GPS_data 缓冲区清零，以便下一次接收新的GPS数据
        memset(GPS_data, 0, sizeof(GPS_data));

    }
}

// 判断接收到的GPS数据是否有效
bool GPS_State(uint16_t data_point)
{   
    bool flag = false;
    for (uint16_t i = 0; i <= 600; i++)
    {
        if (GPS_data[i] == '$' && GPS_data[i + 3] == 'R')
        {
            for (uint8_t j = i + 3; j <= 30; j++)
            {
                if (GPS_data[j] == 'A') //data correct
                {
                    point = j;
                    flag = true;
                    break;
                }
                else if (GPS_data[j] == 'V')
                {
                    point = j;
                    flag = false;
                }
            }
        }
    }

    return flag;
}

void print_coordinates(const char* latitude, const char* n_s, const char* longitude, const char* e_w)
{
    printf("Latitude: %s\n", latitude);
    printf("N_S: %s\n", n_s);
    printf("Longitude: %s\n", longitude);
    printf("E_W: %s\n", e_w);
}

void get_coordinate(void)
{
    // uint8_t count = 0;
    // memset(Latitude, 0, sizeof(Latitude));
    // memset(Longitude, 0, sizeof(Longitude));
    
    // for (uint8_t i = point; i <= 100; i++)
    // {
    //     if (GPS_data[i] == ',')
    //         count++;

    //     switch (count)
    //     {
    //     case 1:
    //         if (GPS_data[i + 1] == '-')
    //             memcpy(Latitude, &GPS_data[i + 1], 11);
    //         else
    //             memcpy(Latitude, &GPS_data[i + 1], 10);
    //         count++;
    //         break;

    //     case 3:
    //         N_S[0] = GPS_data[i + 1];
    //         count++;
    //         break;

    //     case 5:
    //         if (GPS_data[i + 1] == '-')
    //             memcpy(Longitude, &GPS_data[i + 1], 12);
    //         else
    //             memcpy(Longitude, &GPS_data[i + 1], 11);
    //         count++;
    //         break;

    //     case 7:
    //         E_W[0] = GPS_data[i + 1];
    //         count++;
    //         break;

    //     default:
    //         break;
    //     }
    // }
    const char* latitude_false = "32.113286";
    const char* longitude_false = "118.958181";
    print_coordinates(latitude_false, (char*)n_s, longitude_false, (char*)e_w);
    Send_Location_udp((char*)latitude_false, (char*)longitude_false);
    
}



