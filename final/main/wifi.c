#include "esp_wifi.h"
#include <esp_log.h>
#include "freertos/event_groups.h"


#define EXAMPLE_ESP_WIFI_SSID      "HONOR30Pro"
#define EXAMPLE_ESP_WIFI_PASS      "021025021025"
#define EXAMPLE_ESP_WIFI_CHANNEL   1
#define EXAMPLE_MAX_STA_CONN       4

// 联网相关的变量
typedef struct EventGroupDef_t *EventGroupHandle_t;
static EventGroupHandle_t s_wifi_event_group;           // 事件组，用于对wifi响应结果进行标记
static int s_retry_num = 0; 
#define EXAMPLE_ESP_MAXIMUM_RETRY 3
#define WIFI_CONNECTED_BIT BIT0                         // wifi连接成功标志位
#define WIFI_FAIL_BIT      BIT1                         // wifi连接失败标志位
static const char *Wifi_TAG = "WIFI_CONNECT";

/**
 * @description: 处理wifi连接和ip分配时候事件的回调函数
 * @return {*}
 * @note: 
 */
static void event_handler(void* arg, esp_event_base_t event_base,
                                int32_t event_id, void* event_data)
{
    // 如果是wifi station开始连接事件，就尝试将station连接到AP
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START)
    {
        esp_wifi_connect();
    }
    // 如果是wifi station从AP断连事件
    else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED)
    {
        // 如果没有达到最高尝试次数，继续尝试
        if (s_retry_num < EXAMPLE_ESP_MAXIMUM_RETRY)
        {
            esp_wifi_connect();
            s_retry_num++;
            ESP_LOGI(Wifi_TAG, "retry to connect to the AP");
        }
        // 如果达到了最高尝试次数，就标记连接失败
        else
        {
            xEventGroupSetBits(s_wifi_event_group, WIFI_FAIL_BIT);
        }
        ESP_LOGI(Wifi_TAG,"connect to the AP fail");
    }
    else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP)
    {
        ip_event_got_ip_t* event = (ip_event_got_ip_t*) event_data;
        ESP_LOGI(Wifi_TAG, "got ip:" IPSTR, IP2STR(&event->ip_info.ip));
        s_retry_num = 0;
        xEventGroupSetBits(s_wifi_event_group, WIFI_CONNECTED_BIT);     // 成功获取到了ip，就标记这次wifi连接成功
    }
}

/**
 * @description: 用于连接wifi的函数
 * @return {*}
 * @note: 这里wifi连接选项设置了使用nvs，会把每次配置的参数存储在nvs中。因此请查看分区表中是否对nvs分区进行了设置
 */
void wifi_init_sta(void)
{
    // 00 创建wifi事件组
    s_wifi_event_group = xEventGroupCreate();

    /******************** 01 Wi-Fi/LwIP 初始化阶段 ********************/
    // 01-1 创建LWIP核心任务
    ESP_ERROR_CHECK(esp_netif_init());

    // 01-2 创建系统事件任务，并初始化应用程序事件的回调函数
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    // 01-3 创建有 TCP/IP 堆栈的默认网络接口实例绑定 station
    esp_netif_create_default_wifi_sta();

    // 01-4 创建wifi驱动程序任务，并初始化wifi驱动程序
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    // 01-5 注册，用于处理wifi连接的过程中的事件
    esp_event_handler_instance_t instance_any_id;   // 用于处理wifi连接时候的事件的句柄
    esp_event_handler_instance_t instance_got_ip;   // 用于处理ip分配时候产生的事件的句柄
    // 该句柄对wifi连接所有事件都产生响应，连接到event_handler回调函数
    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT,
                                                        ESP_EVENT_ANY_ID,
                                                        &event_handler,
                                                        NULL,
                                                        &instance_any_id));
    // 该句柄仅仅处理IP_EVENT事件组中的从AP中获取ip地址事件，连接到event_handler回调函数
    ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT,
                                                        IP_EVENT_STA_GOT_IP,
                                                        &event_handler,
                                                        NULL,
                                                        &instance_got_ip));

    /******************** 02 WIFI配置阶段 ********************/
    wifi_config_t wifi_config = {
        .sta = {
            .ssid = EXAMPLE_ESP_WIFI_SSID,
            .password = EXAMPLE_ESP_WIFI_PASS,
            /* Setting a password implies station will connect to all security modes including WEP/WPA.
             * However these modes are deprecated and not advisable to be used. Incase your Access point
             * doesn't support WPA2, these mode can be enabled by commenting below line */
         .threshold.authmode = WIFI_AUTH_WPA2_PSK,  // 设置快速扫描模式下能接受的最弱的验证模式
         .sae_pwe_h2e = WPA3_SAE_PWE_BOTH,          // 设置SAE和PWE(wifi协议)的配置
        },
    };
    // 02-2 配置station工作模式
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA) );
    // 02-3 配置
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config) );

    /******************** 03 wifi启动阶段 ********************/
    // 03-1 启动wifi驱动程序
    ESP_ERROR_CHECK(esp_wifi_start() );     // 会触发回调函数

    ESP_LOGI(Wifi_TAG, "wifi_init_sta finished.");

    /* Waiting until either the connection is established (WIFI_CONNECTED_BIT) or connection failed for the maximum
     * number of re-tries (WIFI_FAIL_BIT). The bits are set by event_handler() (see above) */
    /******************** 输出wifi连接结果 ********************/
    EventBits_t bits = xEventGroupWaitBits(s_wifi_event_group,
            WIFI_CONNECTED_BIT | WIFI_FAIL_BIT,
            pdFALSE,
            pdFALSE,
            portMAX_DELAY);

    /* xEventGroupWaitBits() returns the bits before the call returned, hence we can test which event actually
     * happened. */
    if (bits & WIFI_CONNECTED_BIT)
    {
        ESP_LOGI(Wifi_TAG, "connected to ap SSID:%s password:%s",
                 EXAMPLE_ESP_WIFI_SSID, EXAMPLE_ESP_WIFI_PASS);
    }
    else if (bits & WIFI_FAIL_BIT)
    {
        ESP_LOGI(Wifi_TAG, "Failed to connect to SSID:%s, password:%s",
                 EXAMPLE_ESP_WIFI_SSID, EXAMPLE_ESP_WIFI_PASS);
    }
    else
    {
        ESP_LOGE(Wifi_TAG, "UNEXPECTED EVENT");
    }

    /* The event will not be processed after unregister */
    // 05 事件注销
    ESP_ERROR_CHECK(esp_event_handler_instance_unregister(IP_EVENT, IP_EVENT_STA_GOT_IP, instance_got_ip));
    ESP_ERROR_CHECK(esp_event_handler_instance_unregister(WIFI_EVENT, ESP_EVENT_ANY_ID, instance_any_id));
    vEventGroupDelete(s_wifi_event_group);
}