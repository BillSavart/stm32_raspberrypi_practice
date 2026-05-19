/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include "bme68x.h"
#include <stdio.h>

/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
SPI_HandleTypeDef hspi1;

/* USER CODE BEGIN PV */
static struct bme68x_dev bme_dev;
static struct bme68x_conf bme_conf;
static struct bme68x_heatr_conf bme_heatr_conf;
static uint32_t bme_meas_period_us;

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_SPI1_Init(void);
/* USER CODE BEGIN PFP */
static void MX_USART2_UART_Init(void);
static int8_t BME68X_SPI_Read(uint8_t reg_addr, uint8_t *reg_data, uint32_t length, void *intf_ptr);
static int8_t BME68X_SPI_Write(uint8_t reg_addr, const uint8_t *reg_data, uint32_t length, void *intf_ptr);
static void BME68X_DelayUs(uint32_t period, void *intf_ptr);
static int8_t BME68X_InitSensor(void);
static void BME68X_PrintReading(void);

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_SPI1_Init();
  /* USER CODE BEGIN 2 */
  MX_USART2_UART_Init();
  printf("\r\nRoomTemperatureDetector boot\r\n");

  if (BME68X_InitSensor() != BME68X_OK)
  {
    printf("{\"error\":\"bme68x_init_failed\"}\r\n");
    Error_Handler();
  }

  printf("{\"status\":\"bme68x_ready\",\"chip_id\":%u}\r\n", bme_dev.chip_id);

  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
    BME68X_PrintReading();
    HAL_Delay(2000);
  }
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  /** Configure the main internal regulator output voltage
  */
  __HAL_RCC_PWR_CLK_ENABLE();
  __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE3);

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_NONE;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_HSI;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_0) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief SPI1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_SPI1_Init(void)
{

  /* USER CODE BEGIN SPI1_Init 0 */

  /* USER CODE END SPI1_Init 0 */

  /* USER CODE BEGIN SPI1_Init 1 */

  /* USER CODE END SPI1_Init 1 */
  /* SPI1 parameter configuration*/
  hspi1.Instance = SPI1;
  hspi1.Init.Mode = SPI_MODE_MASTER;
  hspi1.Init.Direction = SPI_DIRECTION_2LINES;
  hspi1.Init.DataSize = SPI_DATASIZE_8BIT;
  hspi1.Init.CLKPolarity = SPI_POLARITY_LOW;
  hspi1.Init.CLKPhase = SPI_PHASE_1EDGE;
  hspi1.Init.NSS = SPI_NSS_SOFT;
  hspi1.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_2;
  hspi1.Init.FirstBit = SPI_FIRSTBIT_MSB;
  hspi1.Init.TIMode = SPI_TIMODE_DISABLE;
  hspi1.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
  hspi1.Init.CRCPolynomial = 10;
  if (HAL_SPI_Init(&hspi1) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN SPI1_Init 2 */

  /* USER CODE END SPI1_Init 2 */

}

/**
  * @brief GPIO Initialization Function
  * @param None
  * @retval None
  */
static void MX_GPIO_Init(void)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};
  /* USER CODE BEGIN MX_GPIO_Init_1 */

  /* USER CODE END MX_GPIO_Init_1 */

  /* GPIO Ports Clock Enable */
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOB, GPIO_PIN_6, GPIO_PIN_SET);

  /*Configure GPIO pin : PB6 */
  GPIO_InitStruct.Pin = GPIO_PIN_6;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

  /* USER CODE BEGIN MX_GPIO_Init_2 */

  /* USER CODE END MX_GPIO_Init_2 */
}

/* USER CODE BEGIN 4 */
static void MX_USART2_UART_Init(void)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};
  uint32_t pclk1;
  uint32_t usartdiv;

  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_USART2_CLK_ENABLE();

  GPIO_InitStruct.Pin = GPIO_PIN_2 | GPIO_PIN_3;
  GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStruct.Pull = GPIO_PULLUP;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
  GPIO_InitStruct.Alternate = GPIO_AF7_USART2;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

  USART2->CR1 = 0;
  USART2->CR2 = 0;
  USART2->CR3 = 0;

  pclk1 = HAL_RCC_GetPCLK1Freq();
  usartdiv = (pclk1 + (115200U / 2U)) / 115200U;
  USART2->BRR = usartdiv;
  USART2->CR1 = USART_CR1_TE | USART_CR1_RE | USART_CR1_UE;
}

int __io_putchar(int ch)
{
  while ((USART2->SR & USART_SR_TXE) == 0U)
  {
  }

  USART2->DR = (uint8_t)ch;
  return ch;
}

static void BME68X_Select(void)
{
  HAL_GPIO_WritePin(GPIOB, GPIO_PIN_6, GPIO_PIN_RESET);
}

static void BME68X_Deselect(void)
{
  HAL_GPIO_WritePin(GPIOB, GPIO_PIN_6, GPIO_PIN_SET);
}

static int8_t BME68X_SPI_Read(uint8_t reg_addr, uint8_t *reg_data, uint32_t length, void *intf_ptr)
{
  SPI_HandleTypeDef *hspi = (SPI_HandleTypeDef *)intf_ptr;
  HAL_StatusTypeDef status;

  BME68X_Select();
  status = HAL_SPI_Transmit(hspi, &reg_addr, 1, HAL_MAX_DELAY);
  if (status == HAL_OK)
  {
    status = HAL_SPI_Receive(hspi, reg_data, (uint16_t)length, HAL_MAX_DELAY);
  }
  BME68X_Deselect();

  return (status == HAL_OK) ? BME68X_INTF_RET_SUCCESS : BME68X_E_COM_FAIL;
}

static int8_t BME68X_SPI_Write(uint8_t reg_addr, const uint8_t *reg_data, uint32_t length, void *intf_ptr)
{
  SPI_HandleTypeDef *hspi = (SPI_HandleTypeDef *)intf_ptr;
  HAL_StatusTypeDef status;

  BME68X_Select();
  status = HAL_SPI_Transmit(hspi, &reg_addr, 1, HAL_MAX_DELAY);
  if (status == HAL_OK)
  {
    status = HAL_SPI_Transmit(hspi, (uint8_t *)reg_data, (uint16_t)length, HAL_MAX_DELAY);
  }
  BME68X_Deselect();

  return (status == HAL_OK) ? BME68X_INTF_RET_SUCCESS : BME68X_E_COM_FAIL;
}

static void BME68X_DelayUs(uint32_t period, void *intf_ptr)
{
  (void)intf_ptr;
  HAL_Delay((period + 999U) / 1000U);
}

static int8_t BME68X_InitSensor(void)
{
  int8_t rslt;

  bme_dev.intf = BME68X_SPI_INTF;
  bme_dev.read = BME68X_SPI_Read;
  bme_dev.write = BME68X_SPI_Write;
  bme_dev.delay_us = BME68X_DelayUs;
  bme_dev.intf_ptr = &hspi1;
  bme_dev.amb_temp = 25;

  rslt = bme68x_init(&bme_dev);
  if (rslt != BME68X_OK)
  {
    return rslt;
  }

  bme_conf.os_hum = BME68X_OS_2X;
  bme_conf.os_pres = BME68X_OS_4X;
  bme_conf.os_temp = BME68X_OS_8X;
  bme_conf.filter = BME68X_FILTER_SIZE_3;
  bme_conf.odr = BME68X_ODR_NONE;

  rslt = bme68x_set_conf(&bme_conf, &bme_dev);
  if (rslt != BME68X_OK)
  {
    return rslt;
  }

  bme_heatr_conf.enable = BME68X_ENABLE;
  bme_heatr_conf.heatr_temp = 320;
  bme_heatr_conf.heatr_dur = 150;

  rslt = bme68x_set_heatr_conf(BME68X_FORCED_MODE, &bme_heatr_conf, &bme_dev);
  if (rslt != BME68X_OK)
  {
    return rslt;
  }

  bme_meas_period_us = bme68x_get_meas_dur(BME68X_FORCED_MODE, &bme_conf, &bme_dev) +
                       ((uint32_t)bme_heatr_conf.heatr_dur * 1000U);

  return BME68X_OK;
}

static void BME68X_PrintReading(void)
{
  int8_t rslt;
  struct bme68x_data data;
  uint8_t n_data = 0;
  int32_t temperature_c_x100;
  uint32_t humidity_rh_x100;
  uint32_t pressure_pa;
  uint32_t gas_ohm;
  uint8_t gas_valid;
  uint8_t heat_stable;

  rslt = bme68x_set_op_mode(BME68X_FORCED_MODE, &bme_dev);
  if (rslt != BME68X_OK)
  {
    printf("{\"error\":\"set_forced_mode_failed\",\"code\":%d}\r\n", rslt);
    return;
  }

  BME68X_DelayUs(bme_meas_period_us, bme_dev.intf_ptr);

  rslt = bme68x_get_data(BME68X_FORCED_MODE, &data, &n_data, &bme_dev);
  if (rslt != BME68X_OK)
  {
    printf("{\"error\":\"read_failed\",\"code\":%d}\r\n", rslt);
    return;
  }

  if (n_data == 0)
  {
    printf("{\"warning\":\"no_new_data\"}\r\n");
    return;
  }

  temperature_c_x100 = (int32_t)(data.temperature * 100.0f);
  humidity_rh_x100 = (uint32_t)(data.humidity * 100.0f);
  pressure_pa = (uint32_t)data.pressure;
  gas_ohm = (uint32_t)data.gas_resistance;
  gas_valid = (data.status & BME68X_GASM_VALID_MSK) ? 1U : 0U;
  heat_stable = (data.status & BME68X_HEAT_STAB_MSK) ? 1U : 0U;

  printf("{\"temperature_c_x100\":%ld,\"humidity_rh_x100\":%lu,"
         "\"pressure_pa\":%lu,\"gas_ohm\":%lu,"
         "\"gas_valid\":%u,\"heat_stable\":%u}\r\n",
         (long)temperature_c_x100,
         (unsigned long)humidity_rh_x100,
         (unsigned long)pressure_pa,
         (unsigned long)gas_ohm,
         gas_valid,
         heat_stable);
}

/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}
#ifdef USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
