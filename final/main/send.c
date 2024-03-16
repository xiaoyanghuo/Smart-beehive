
#include "cJSON.h"
#include "esp_err.h"
#include "esp_tls.h"
#include <esp_log.h>

// http
#include "esp_http_client.h"
// udp
#include "lwip/sockets.h"
#include "lwip/sys.h"
#include <lwip/netdb.h>


//HTTP client
#define MAX_HTTP_RECV_BUFFER 2048
#define MAX_HTTP_OUTPUT_BUFFER 4096
static const char *TAG = "UDP_CLIENT";

#define portTICK_RATE_MS portTICK_PERIOD_MS
#define portTICK_PERIOD_MS	( ( TickType_t ) 1000 / configTICK_RATE_HZ )

#define HOST_IP_ADDR "192.168.43.192"
#define PORT 8000

esp_err_t _http_event_handler(esp_http_client_event_t *evt)
{
    static char *output_buffer;  // Buffer to store response of http request from event handler
    static int output_len;       // Stores number of bytes read
    switch(evt->event_id) {
        case HTTP_EVENT_ERROR:
            ESP_LOGD(TAG, "HTTP_EVENT_ERROR");
            break;
        case HTTP_EVENT_ON_CONNECTED:
            ESP_LOGD(TAG, "HTTP_EVENT_ON_CONNECTED");
            break;
        case HTTP_EVENT_HEADER_SENT:
            ESP_LOGD(TAG, "HTTP_EVENT_HEADER_SENT");
            break;
        case HTTP_EVENT_ON_HEADER:
            ESP_LOGD(TAG, "HTTP_EVENT_ON_HEADER, key=%s, value=%s", evt->header_key, evt->header_value);
            break;
        case HTTP_EVENT_ON_DATA:
            ESP_LOGD(TAG, "HTTP_EVENT_ON_DATA, len=%d", evt->data_len);
            /*
             *  Check for chunked encoding is added as the URL for chunked encoding used in this example returns binary data.
             *  However, event handler can also be used in case chunked encoding is used.
             */
            if (!esp_http_client_is_chunked_response(evt->client)) {
                // If user_data buffer is configured, copy the response into the buffer
                if (evt->user_data) {
                    memcpy(evt->user_data + output_len, evt->data, evt->data_len);
                } else {
                    if (output_buffer == NULL) {
                        output_buffer = (char *) malloc(esp_http_client_get_content_length(evt->client));
                        output_len = 0;
                        if (output_buffer == NULL) {
                            ESP_LOGE(TAG, "Failed to allocate memory for output buffer");
                            return ESP_FAIL;
                        }
                    }
                    memcpy(output_buffer + output_len, evt->data, evt->data_len);
                }
                output_len += evt->data_len;
            }

            break;
        case HTTP_EVENT_ON_FINISH:
            ESP_LOGD(TAG, "HTTP_EVENT_ON_FINISH");
            if (output_buffer != NULL) {
                // Response is accumulated in output_buffer. Uncomment the below line to print the accumulated response
                // ESP_LOG_BUFFER_HEX(TAG, output_buffer, output_len);
                free(output_buffer);
                output_buffer = NULL;
            }
            output_len = 0;
            break;
        case HTTP_EVENT_DISCONNECTED:
            ESP_LOGI(TAG, "HTTP_EVENT_DISCONNECTED");
            int mbedtls_err = 0;
            esp_err_t err = esp_tls_get_and_clear_last_error((esp_tls_error_handle_t)evt->data, &mbedtls_err, NULL);
            if (err != 0) {
                ESP_LOGI(TAG, "Last esp error code: 0x%x", err);
                ESP_LOGI(TAG, "Last mbedtls failure: 0x%x", mbedtls_err);
            }
            if (output_buffer != NULL) {
                free(output_buffer);
                output_buffer = NULL;
            }
            output_len = 0;
            break;
        case HTTP_EVENT_REDIRECT:
            ESP_LOGD(TAG, "HTTP_EVENT_REDIRECT");
            esp_http_client_set_header(evt->client, "From", "user@example.com");
            esp_http_client_set_header(evt->client, "Accept", "text/html");
            esp_http_client_set_redirection(evt->client);
            break;
    }
    return ESP_OK;
}

void Sender_udp(const char * buffer, int length)
{
    int addr_family = 0;
    int ip_protocol = 0;

    //define dest_ip_port
    struct sockaddr_in dest_addr;
    dest_addr.sin_addr.s_addr = inet_addr(HOST_IP_ADDR);
    dest_addr.sin_family = AF_INET;
    dest_addr.sin_port = htons(PORT);

    //set socket
    addr_family = AF_INET;
    ip_protocol = IPPROTO_IP;
    int sock = socket(addr_family, SOCK_DGRAM, ip_protocol);
    if (sock < 0) {
        ESP_LOGE(TAG, "Unable to create socket: errno %d", errno);
        return;
    }
    struct timeval timeout; timeout.tv_sec = 10; timeout.tv_usec = 0;// Set timeout
    setsockopt (sock, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof timeout);
    ESP_LOGI(TAG, "Socket created, sending to %s:%d", HOST_IP_ADDR, PORT);

    //send udp datagram
    int err = sendto(sock, buffer, length, 0, (struct sockaddr *)&dest_addr, sizeof(dest_addr));
    printf("send length: %d", length);
    if (err < 0) {
        ESP_LOGE(TAG, "Error occurred during sending: errno %d", errno);
        return;
    }
    
    //finish sending
    shutdown(sock, 0);
    close(sock);
    return ;
}

void Sender_HTTP(const char* buffer, int length, const char *type){
    char local_response_buffer[MAX_HTTP_OUTPUT_BUFFER] = {0};
    esp_http_client_config_t config = {
        .host = "192.168.43.192:8000",
        .path = "/",
        .disable_auto_redirect = true,
        .event_handler = _http_event_handler,
        .user_data = local_response_buffer,
    };
    esp_http_client_handle_t data_client = esp_http_client_init(&config);
    esp_err_t err;
    esp_http_client_set_url(data_client, "http://192.168.43.192:8000/");
    esp_http_client_set_method(data_client, HTTP_METHOD_POST);
    esp_http_client_set_header(data_client, "Content-Type", type);
    esp_http_client_set_post_field(data_client, (const char *)buffer, length);
    err = esp_http_client_perform(data_client);
}

void SendData(float humidity, float temperature, float weight){
    char local_response_buffer[MAX_HTTP_OUTPUT_BUFFER] = {0};
    esp_http_client_config_t config = {
        .host = "192.168.43.192:8000",
        .path = "/",
        .disable_auto_redirect = true,
        .event_handler = _http_event_handler,
        .user_data = local_response_buffer,        // Pass address of local buffer to get response
    };
    printf("send Humidity,Temperature and Weight\n");
    esp_http_client_handle_t data_client = esp_http_client_init(&config);
    esp_err_t err;
    esp_http_client_set_url(data_client, "http://192.168.43.192:8000/");
    esp_http_client_set_method(data_client, HTTP_METHOD_POST);
    // content类型设置为data，表示发送的数据是温度，湿度，重量
    esp_http_client_set_header(data_client, "Content-Type", "application/json");
    // Create a JSON object and add weight,humidity and temperature information
    cJSON *json_object = cJSON_CreateObject();
    cJSON_AddNumberToObject(json_object, "humidity", humidity);
    cJSON_AddNumberToObject(json_object, "temperature", temperature);
    cJSON_AddNumberToObject(json_object, "weight", weight);
    char *json_data = cJSON_Print(json_object);
    int length = strlen(json_data);
    uint8_t *combined_data = (uint8_t *)malloc(length + 1);
    // memcpy(combined_data, fb->buf, fb->len);
    // memcpy(combined_data + fb->len, json_data, strlen(json_data));
    memcpy(combined_data,json_data,length);
    combined_data[length] = '\0';
    esp_http_client_set_post_field(data_client, (const char *)combined_data, length);
    err = esp_http_client_perform(data_client);
    printf("send over\n");
    free(combined_data);
    free(json_data);
    cJSON_Delete(json_object);
}

void SendLocation(const char* latitude, const char* longitude){
    char local_response_buffer[MAX_HTTP_OUTPUT_BUFFER] = {0};
    esp_http_client_config_t config = {
        .host = "192.168.43.192:8000",
        .path = "/",
        .disable_auto_redirect = true,
        .event_handler = _http_event_handler,
        .user_data = local_response_buffer,        // Pass address of local buffer to get response
    };
    printf("send Location information\n");
    esp_http_client_handle_t data_client = esp_http_client_init(&config);
    esp_err_t err;
    esp_http_client_set_url(data_client, "http://192.168.43.192:8000/");
    esp_http_client_set_method(data_client, HTTP_METHOD_POST);
    // content类型设置为GPS,表示发送的信息是位置信息
    esp_http_client_set_header(data_client, "Content-Type", "GPS");
    // Create a JSON object and add weight,humidity and temperature information
    cJSON *json_object = cJSON_CreateObject();
    double lat = atof(latitude);
    double longi = atof(longitude);
    cJSON_AddNumberToObject(json_object, "latitude", lat);
    // cJSON_AddNumberToObject(json_object, "n_s", N_S);
    cJSON_AddNumberToObject(json_object, "longitude", longi);
    // cJSON_AddNumberToObject(json_object, "e_w", E_W);
    // cJSON_AddNumberToObject(json_object, "weight", weight);
    char *json_data = cJSON_Print(json_object);
    int length = strlen(json_data);
    uint8_t *combined_data = (uint8_t *)malloc(length + 1);
    // memcpy(combined_data, fb->buf, fb->len);
    // memcpy(combined_data + fb->len, json_data, strlen(json_data));
    memcpy(combined_data,json_data,length);
    combined_data[length] = '\0';
    esp_http_client_set_post_field(data_client, (const char *)combined_data, length);
    err = esp_http_client_perform(data_client);
    free(combined_data);
    free(json_data);
    cJSON_Delete(json_object);
}

void Send_HTW_udp(float humidity, float temperature, float weight){
    //print
    printf("send Humidity,Temperature and Weight\n");

    //Create a JSON object and add weight,humidity and temperature information

    cJSON *json_object = cJSON_CreateObject();
    cJSON_AddNumberToObject(json_object, "humidity", humidity);
    cJSON_AddNumberToObject(json_object, "temperature", temperature);
    cJSON_AddNumberToObject(json_object, "weight", weight);
    char *json_data = cJSON_Print(json_object);
    int length = strlen(json_data);
    uint8_t *combined_data = (uint8_t *)malloc(length + 1);
    memcpy(combined_data,json_data,length);
    combined_data[length] = '\0';

    //send udp datagram
    Sender_udp((const char *)combined_data, length);

    //postpostprocess
    free(combined_data);
    free(json_data);
    cJSON_Delete(json_object);
}

void Send_Location_udp(const char* latitude, const char* longitude){
    //print
    printf("send Location information\n");

    //Construct JSON message
    cJSON *json_object = cJSON_CreateObject();
    double lat = atof(latitude);
    double longi = atof(longitude);
    cJSON_AddNumberToObject(json_object, "latitude", lat);
    // cJSON_AddNumberToObject(json_object, "n_s", N_S);
    cJSON_AddNumberToObject(json_object, "longitude", longi);
    // cJSON_AddNumberToObject(json_object, "e_w", E_W);
    char *json_data = cJSON_Print(json_object);
    int length = strlen(json_data);
    uint8_t *combined_data = (uint8_t *)malloc(length + 1);
    memcpy(combined_data,json_data,length);
    combined_data[length] = '\0';

    //send udp datagram
    Sender_udp((const char *)combined_data, length);

    //postprocess
    free(combined_data);
    free(json_data);
    cJSON_Delete(json_object);
}

void Send_Image_udp(const char * buffer, int length){
    //send udp datagram
    Sender_udp(buffer, length);
}

