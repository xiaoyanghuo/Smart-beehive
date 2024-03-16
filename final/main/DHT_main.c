#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_system.h"
#include "rom/ets_sys.h"
#include "nvs_flash.h"
#include "driver/gpio.h"
#include "sdkconfig.h"

#include "DHT22.h"

void DHT_task()
{
	// setDHTgpio( 14 );
	// printf( "Starting DHT Task\n\n");
	int timer = 0;
	while(1) {
		timer++;
		printf("timer:%d",timer);
		printf("=== Reading DHT ===\n" );
		int ret = readDHT();
		
		errorHandler(ret);

		printf( "Hum %.1f\n", getHumidity() );
		printf( "Tmp %.1f\n", getTemperature() );
		
		// -- wait at least 2 sec before reading again ------------
		// The interval of whole process must be beyond 2 seconds !! 
		vTaskDelay( 1000 / portTICK_PERIOD_MS );
	}
}

// void app_main()
// {
// 	nvs_flash_init();
// 	xTaskCreate( &DHT_task, "DHT_task", 2048, NULL, 5, NULL );
// }

