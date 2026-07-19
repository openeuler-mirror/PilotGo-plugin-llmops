package config

import (
	"errors"
	"fmt"
	"os"
	"strings"

	"gitee.com/openeuler/PilotGo-plugin-llmops/server/pkg/logger"
	"gopkg.in/yaml.v2"
)

// Config 是 PilotGo Client 的配置入口，仅包含当前已实现模块所需的字段。
type Config struct {
	// Server 服务端连接配置
	Server ServerConfig `yaml:"server"`

	// Client 客户端自身身份配置
	Client ClientIdentity `yaml:"client"`

	// Log 日志配置
	Log logger.LoggerConfig `yaml:"log"`
}

// ServerConfig 定义与服务端相关的配置。
type ServerConfig struct {
	// Addr WebSocket 服务端地址，例如 ws://localhost:8080/ws
	Addr string `yaml:"addr"`
}

// ClientIdentity 定义客户端身份配置。
type ClientIdentity struct {
	// ID 客户端唯一标识，为空时默认使用 hostname
	ID string `yaml:"id"`

	// Token 连接服务端使用的鉴权令牌
	Token string `yaml:"token"`
}

// LoadConfig 从指定路径读取 YAML 配置文件并返回 Config。
// 若文件不存在或解析失败则返回错误。
func LoadConfig(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read config file %s failed: %w", path, err)
	}

	cfg := &Config{}
	if err := yaml.Unmarshal(data, cfg); err != nil {
		return nil, fmt.Errorf("parse config file %s failed: %w", path, err)
	}

	cfg.setDefaults()
	if err := cfg.validate(); err != nil {
		return nil, fmt.Errorf("validate config failed: %w", err)
	}

	return cfg, nil
}

// MustLoadConfig 与 LoadConfig 类似，出错时直接退出程序。
func MustLoadConfig(path string) *Config {
	cfg, err := LoadConfig(path)
	if err != nil {
		logger.Fatalf("load config failed: %v", err)
	}
	return cfg
}

// InitLogger 使用配置中的日志配置初始化全局 logger。
func (c *Config) InitLogger() {
	logger.Init(&c.Log)
}

// ClientID 返回客户端 ID，若未配置则返回当前主机名。
func (c *Config) ClientID() string {
	if c.Client.ID != "" {
		return c.Client.ID
	}
	hostname, err := os.Hostname()
	if err != nil {
		return "unknown"
	}
	return hostname
}

// setDefaults 为缺失的配置项设置默认值。
func (c *Config) setDefaults() {
	if strings.TrimSpace(c.Log.Level) == "" {
		c.Log.Level = "info"
	}
}

// validate 校验配置合法性。
func (c *Config) validate() error {
	if strings.TrimSpace(c.Server.Addr) == "" {
		return errors.New("server.addr is required")
	}

	if strings.TrimSpace(c.Client.Token) == "" {
		return errors.New("client.token is required")
	}

	return nil
}
