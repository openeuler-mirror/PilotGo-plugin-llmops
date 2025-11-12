package config

import (
	"log"
	"os"

	"gopkg.in/yaml.v2"

	"gitee.com/openeuler/PilotGo-plugin-llmops/server/logger"
)

type Config struct {
	Server struct {
		Host string `yaml:"host"`
		Port int    `yaml:"port"`
	} `yaml:"server"`
	DB struct {
		Host     string `yaml:"host"`
		Port     int    `yaml:"port"`
		User     string `yaml:"user"`
		Password string `yaml:"password"`
		Database string `yaml:"database"`
	} `yaml:"db"`
	Log logger.LoggerConfig `yaml:"log"`
}

var globalConfig *Config

func GetConfig() *Config {
	return globalConfig
}

func InitConfig() {
	config, err := loadConfig()
	if err != nil {
		log.Fatalf("load config failed: %v", err)
	}
	globalConfig = config
}

func loadConfig() (*Config, error) {
	config := &Config{}
	data, err := os.ReadFile("./config.yaml")
	if err != nil {
		return nil, err
	}
	err = yaml.Unmarshal(data, config)
	if err != nil {
		return nil, err
	}
	return config, nil
}
