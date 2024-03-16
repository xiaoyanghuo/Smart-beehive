#include "HX711.h"
#include "esp_log.h"
#include <rom/ets_sys.h>

#define HIGH 1
#define LOW 0
#define CLOCK_DELAY_US 20	// 控制时钟的延迟时间

#define DEBUGTAG "HX711"
static gpio_num_t GPIO_PD_SCK;	// Power Down and Serial Clock Input Pin
static gpio_num_t GPIO_DOUT;		// Serial Data Output Pin
static HX711_GAIN GAIN = eGAIN_128;		// amplification factor
static unsigned long OFFSET = 0;	// used for tare weight
static float SCALE = 1;	// used to return weight in grams, kg, ounces, whatever

// 初始化HX711模块
void HX711_init(gpio_num_t dout, gpio_num_t pd_sck, HX711_GAIN gain )
{
	GPIO_PD_SCK = pd_sck;
	GPIO_DOUT = dout;

	gpio_config_t io_conf;
    io_conf.intr_type = 0;
    io_conf.mode = GPIO_MODE_OUTPUT;
    io_conf.pin_bit_mask = (1UL<<GPIO_PD_SCK);
    io_conf.pull_down_en = 0;
    io_conf.pull_up_en = 0;
    gpio_config(&io_conf);

    io_conf.intr_type = 0;
    io_conf.pin_bit_mask = (1UL<<GPIO_DOUT);
    io_conf.mode = GPIO_MODE_INPUT;
    io_conf.pull_up_en = 0;
	gpio_config(&io_conf);

	HX711_set_gain(gain);
}

// 通过检查引脚的电平状态来判断HX711模块是否准备好进行读取
bool HX711_is_ready()
{
	return gpio_get_level(GPIO_DOUT);
}

// 通过控制时钟引脚的电平来设置增益
void HX711_set_gain(HX711_GAIN gain)
{
	GAIN = gain;
	gpio_set_level(GPIO_PD_SCK, LOW);
	HX711_read();
}

// 从HX711模块读取8位数据
uint8_t HX711_shiftIn()
{
	uint8_t value = 0;

    for(int i = 0; i < 8; ++i) 
    {
        gpio_set_level(GPIO_PD_SCK, HIGH);
        ets_delay_us(CLOCK_DELAY_US);
        value |= gpio_get_level(GPIO_DOUT) << (7 - i); //get level returns 
        gpio_set_level(GPIO_PD_SCK, LOW);
        ets_delay_us(CLOCK_DELAY_US);
    }

    return value;
}

// 从HX711模块读取24位数据
unsigned long HX711_read()
{
	gpio_set_level(GPIO_PD_SCK, LOW);
	// wait for the chip to become ready
	while (HX711_is_ready()) 
	{
		vTaskDelay(10 / portTICK_PERIOD_MS);
	}

	unsigned long value = 0;

	//--- Enter critical section ----
	portDISABLE_INTERRUPTS();

	for(int i=0; i < 24 ; i++)
	{   
		gpio_set_level(GPIO_PD_SCK, HIGH);
        ets_delay_us(CLOCK_DELAY_US);
        value = value << 1;
        gpio_set_level(GPIO_PD_SCK, LOW);
        ets_delay_us(CLOCK_DELAY_US);

        if(gpio_get_level(GPIO_DOUT))
        	value++;
	}

	// set the channel and the gain factor for the next reading using the clock pin
	for (unsigned int i = 0; i < GAIN; i++) 
	{	
		gpio_set_level(GPIO_PD_SCK, HIGH);
		ets_delay_us(CLOCK_DELAY_US);
		gpio_set_level(GPIO_PD_SCK, LOW);
		ets_delay_us(CLOCK_DELAY_US);
	}	
	portENABLE_INTERRUPTS();
	//--- Exit critical section ----

	value =value^0x800000;

	return (value);
}


// 多次读取数据并计算平均值
unsigned long  HX711_read_average(char times) 
{
	// ESP_LOGI(DEBUGTAG, "===================== READ AVERAGE START ====================");
	unsigned long sum = 0;
	for (char i = 0; i < times; i++) 
	{
		sum += HX711_read();
	}
	// ESP_LOGI(DEBUGTAG, "===================== READ AVERAGE END ====================");
	return sum / times;
}

// 获取去除偏移值后的重量数据
unsigned long HX711_get_value(char times) 
{
	unsigned long avg = HX711_read_average(times);
	if(avg > OFFSET)
		return avg - OFFSET;
	else
		return 0;
}

// 获取转换后的重量数据(返回的是去除偏移值并经过比例系数转换后的重量值)
float HX711_get_units(char times) 
{
	return HX711_get_value(times) / SCALE;
}

// 进行初始校准
void HX711_tare( ) 
{
	ESP_LOGI(DEBUGTAG, "===================== START TARE ====================");
	unsigned long sum = 0; 
	sum = HX711_read_average(20);
	HX711_set_offset(sum);
	ESP_LOGI(DEBUGTAG, "===================== END TARE: %ld ====================",sum);
}

// 设置比例系数(如果比例系数是以克为单位的，则返回的重量也将以克为单位)
void HX711_set_scale(float scale ) 
{
	SCALE = scale;
}

// 获取比例系数
float HX711_get_scale()
 {
	return SCALE;
}

// 设置偏移值
void HX711_set_offset(unsigned long offset)
 {
	OFFSET = offset;
}

// 获取偏移值
unsigned long HX711_get_offset(unsigned long offset) 
{
	return OFFSET;
}

// 将HX711模块置于电源关闭状态
void HX711_power_down() 
{
	gpio_set_level(GPIO_PD_SCK, LOW);
	ets_delay_us(CLOCK_DELAY_US);
	gpio_set_level(GPIO_PD_SCK, HIGH);
	ets_delay_us(CLOCK_DELAY_US);
}

// 将HX711模块置于电源开启状态
void HX711_power_up() 
{
	gpio_set_level(GPIO_PD_SCK, LOW);
}
