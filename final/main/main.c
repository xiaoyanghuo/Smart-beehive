#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <esp_log.h>
#include <esp_camera.h>
#include <esp_event.h>
#include <esp_wifi.h>
#include <esp_system.h>
#include <sys/param.h>
#include <string.h>
#include <sys/socket.h>
#include "esp_err.h"
#include "esp_tls.h"
#include "nvs_flash.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include <freertos/stream_buffer.h>
#include <freertos/event_groups.h>
#include "GPS.c"
#include "DHT22.h"
#include "HX711.h"
#include "esp_http_client.h"
#include "cJSON.h"
#include "wifi.c"


// 温湿度引脚
#define DHT22_pin (14)
// 重量模块引脚
#define GPIO_DATA   GPIO_NUM_13
#define GPIO_SCLK   GPIO_NUM_11 
#define HIGH 1
#define LOW 0

#define CAM_PIN_PWDN    (18)
#define CAM_PIN_RESET   (42) //software reset will be performed
#define CAM_PIN_XCLK    (-1)
#define CAM_PIN_SIOD    (5)
#define CAM_PIN_SIOC    ( 4)
#define CAM_PIN_D7      (38)
#define CAM_PIN_D6      (16)
#define CAM_PIN_D5      (39)
#define CAM_PIN_D4      (15)
#define CAM_PIN_D3      (40)
#define CAM_PIN_D2      (7)
#define CAM_PIN_D1      (41)
#define CAM_PIN_D0      (6)
#define CAM_PIN_VSYNC   (1)
#define CAM_PIN_HREF    (2)
#define CAM_PIN_PCLK    (17)

camera_config_t config;



void my_loop(){
    int ret;
    float temp = 27.0; // 温度 
    float hum = 63.2; // 湿度
    float weight = 0.0;// 重量
    int timer = 0;// 小计时器
    int XWC_Timer = 0;// 大计时器
    printf("start\n");
    vTaskDelay(3000/portTICK_RATE_MS);
    while(1){
        // http_rest_with_url();

        //camera
        camera_fb_t *fb = esp_camera_fb_get();
        if (!fb)
        {
            ESP_LOGE(TAG, "Camera capture failed!");
            return ;
        }
        ESP_LOGI(TAG, "Camera capture succeeded!");
        Send_Image_udp((const char *)fb->buf, fb->len);
        esp_camera_fb_return(fb);
        if(timer!=50)
            vTaskDelay(160/portTICK_RATE_MS);
        timer++;
        printf("timer = %d\n",timer);
        // 小计时器计时若干次，获取一次温湿度和重量
        if(timer==50){
            timer = 0;
            XWC_Timer+=1;
            // 读温湿度
            ret = readDHT();
            if(ret==DHT_OK){
                temp = getTemperature();
                hum = getHumidity();
                // SendData(hum,temp);
            }
            // 读重量
            weight = (HX711_get_units(AVG_SAMPLES)) / 500000.0f; // 单位是kg
            printf( "Humidity: %.1f\n", hum);
            printf( "Temperature: %.1f\n", temp);
            printf( "Weight:%.1f\n",weight); 
            // ESP_LOGI("重量", "===================== READ WEIGHT START ====================");
            // ESP_LOGI("重量", "******* weight = %.2f kg *********\n ", weight);
        }
        if(XWC_Timer==2){
            XWC_Timer = 0;
            printf( "Humidity: %.1f\n", hum);
            printf( "Temperature: %.1f\n", temp);
            printf( "Weight:%.1f\n",weight); 
            Send_HTW_udp(hum,temp,weight);
        }
        // errorHandler(ret);
        
    }
}


void app_main() {
    /*------------------camera引脚及其设置---------------------*/
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_pwdn = CAM_PIN_PWDN;
    config.pin_reset = CAM_PIN_RESET;
    config.pin_xclk = CAM_PIN_XCLK;
    config.pin_sccb_sda = CAM_PIN_SIOD;
    config.pin_sccb_scl = CAM_PIN_SIOC;

    config.pin_d7 = CAM_PIN_D7;
    config.pin_d6 = CAM_PIN_D6;
    config.pin_d5 = CAM_PIN_D5;
    config.pin_d4 = CAM_PIN_D4;
    config.pin_d3 = CAM_PIN_D3;
    config.pin_d2 = CAM_PIN_D2;
    config.pin_d1 = CAM_PIN_D1;
    config.pin_d0 = CAM_PIN_D0;
    config.pin_vsync = CAM_PIN_VSYNC;
    config.pin_href = CAM_PIN_HREF;
    config.pin_pclk = CAM_PIN_PCLK;

    config.xclk_freq_hz = 20000000; //EXPERIMENTAL: Set to 16MHz on ESP32-S2 or ESP32-S3 to enable EDMA mode
    config.ledc_timer = LEDC_TIMER_0;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.pixel_format = PIXFORMAT_JPEG; //YUV422,GRAYSCALE,RGB565,JPEG
    config.frame_size = FRAMESIZE_VGA;    //QQVGA-UXGA, For ESP32, do not use sizes above QVGA when not JPEG. The performance of the ESP32-S series has improved a lot, but JPEG mode always gives better frame rates.
    config.jpeg_quality = 4; //0-63, for OV series camera sensors, lower number means higher quality
    config.fb_count = 2; //When jpeg mode is used, if fb_count more than one, the driver will work in continuous mode.
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY; //CAMERA_GRAB_LATEST. Sets when buffers should be filled

    /*-----------------NVS初始化----------------------*/
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
    ESP_ERROR_CHECK(nvs_flash_erase());
    ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);
    /*----------------wifi连接------------------------*/
    ESP_LOGI("WIFI:", "ESP_WIFI_MODE_STA!");
    wifi_init_sta();    // 初始化WiFi连接
    /*----------------GPS初始化并获取经纬度信息-----------------------*/
    init_GPS();
    rx_task();
    // const char* latitude_false = "45.74545";
    // const char* longitude_false = "126.63205";
    // print_coordinates(latitude_false, (char*)n_s, longitude_false, (char*)e_w);
    // Send_Location_udp((char*)latitude_false, (char*)longitude_false);
    /*----------------相机初始化----------------------*/
    esp_err_t err = esp_camera_init(&config);
    while (err != ESP_OK) {
        ESP_LOGE(TAG, "Camera initialization failed!");
        err = esp_camera_init(&config);
    }
    sensor_t * s = esp_camera_sensor_get();
    s->set_brightness(s, 2);    // -2 to 2
    s->set_contrast(s, 2);       // -2 to 2
    s->set_saturation(s, -2);     // -2 to 2
    s->set_special_effect(s, 0); // 0 to 6 (0 - No Effect, 1 - Negative, 2 - Grayscale, 3 - Red Tint, 4 - Green Tint, 5 - Blue Tint, 6 - Sepia)
    s->set_whitebal(s, 1);       // 0 = disable , 1 = enable
    s->set_awb_gain(s, 1);       // 0 = disable , 1 = enable
    s->set_wb_mode(s, 0);        // 0 to 4 - if awb_gain enabled (0 - Auto, 1 - Sunny, 2 - Cloudy, 3 - Office, 4 - Home)
    s->set_exposure_ctrl(s, 1);  // 0 = disable , 1 = enable
    s->set_aec2(s, 1);           // 0 = disable , 1 = enable
    s->set_ae_level(s, 2);       // -2 to 2
    s->set_aec_value(s, 300);    // 0 to 1200
    s->set_gain_ctrl(s, 1);      // 0 = disable , 1 = enable
    s->set_agc_gain(s, 0);       // 0 to 30
    s->set_gainceiling(s, (gainceiling_t)0);  // 0 to 6
    s->set_bpc(s, 0);            // 0 = disable , 1 = enable
    s->set_wpc(s, 1);            // 0 = disable , 1 = enable
    s->set_raw_gma(s, 1);        // 0 = disable , 1 = enable
    s->set_lenc(s, 1);           // 0 = disable , 1 = enable

    s->set_hmirror(s, 0);        // 0 = disable , 1 = enable
    s->set_vflip(s, 0);          // 0 = disable , 1 = enable
    s->set_dcw(s, 1);            // 0 = disable , 1 = enable
    s->set_colorbar(s, 0);       // 0 = disable , 1 = enable
    ESP_LOGI(TAG, "Camera initialization succeeded!");
    
    ESP_ERROR_CHECK(esp_netif_init());

    /*--------------初始化温湿度传感器----------------------*/
    //设置温湿度传感器引脚
    setDHTgpio( DHT22_pin );

    /*--------------初始化称重传感器----------------------*/
	// // 初始化HX711模块,设置增益为128
	HX711_init(GPIO_DATA,GPIO_SCLK,eGAIN_128); 
    // // // 进行初始校准
    HX711_tare(); 

    // 开始我们的循环任务~
    // xTaskCreate(&tempStatic,"STATIC-METHOD",44096,NULL,5,NULL);
    my_loop();

}
