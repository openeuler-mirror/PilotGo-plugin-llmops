package db

import (
	"fmt"
	"log"
	"time"

	"gitee.com/openeuler/PilotGo-plugin-llmops/server/config"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

var DB *gorm.DB

// InitDB 初始化数据库连接
func InitDB() error {
	cfg := config.GetConfig()

	// 先连接到 MySQL server（不指定 database），自动创建数据库
	serverDsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/?charset=utf8mb4&parseTime=True&loc=Local",
		cfg.DB.User,
		cfg.DB.Password,
		cfg.DB.Host,
		cfg.DB.Port,
	)
	serverDB, err := gorm.Open(mysql.Open(serverDsn), &gorm.Config{})
	if err != nil {
		return fmt.Errorf("failed to connect mysql server: %v", err)
	}
	createSQL := fmt.Sprintf("CREATE DATABASE IF NOT EXISTS `%s` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci", cfg.DB.Database)
	if err := serverDB.Exec(createSQL).Error; err != nil {
		return fmt.Errorf("failed to create database: %v", err)
	}
	sqlDB, err := serverDB.DB()
	if err == nil {
		_ = sqlDB.Close()
	}

	dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/%s?charset=utf8mb4&parseTime=True&loc=Local",
		cfg.DB.User,
		cfg.DB.Password,
		cfg.DB.Host,
		cfg.DB.Port,
		cfg.DB.Database,
	)

	// 配置GORM日志
	newLogger := logger.New(
		log.New(log.Writer(), "\r\n", log.LstdFlags), // io writer
		logger.Config{
			SlowThreshold:             3 * time.Second, // 慢SQL阈值
			LogLevel:                  logger.Silent,   // 日志级别
			IgnoreRecordNotFoundError: true,            // 忽略ErrRecordNotFound错误
			ParameterizedQueries:      true,            // 不在SQL日志中包含参数
			Colorful:                  false,           // 禁用彩色打印
		},
	)

	// 连接数据库
	DB, err = gorm.Open(mysql.Open(dsn), &gorm.Config{
		Logger: newLogger,
	})
	if err != nil {
		return fmt.Errorf("failed to connect database: %v", err)
	}

	// 获取底层的sql.DB对象来配置连接池
	sqlDB, err = DB.DB()
	if err != nil {
		return fmt.Errorf("failed to get underlying sql.DB: %v", err)
	}

	// 设置连接池参数
	sqlDB.SetMaxOpenConns(25)                 // 设置最大打开连接数
	sqlDB.SetMaxIdleConns(25)                 // 设置最大空闲连接数
	sqlDB.SetConnMaxLifetime(5 * time.Minute) // 设置连接最大生存时间

	// 测试连接
	if err = sqlDB.Ping(); err != nil {
		return fmt.Errorf("failed to ping database: %v", err)
	}

	return nil
}

// Close 关闭数据库连接
func Close() error {
	if DB != nil {
		sqlDB, err := DB.DB()
		if err != nil {
			return fmt.Errorf("failed to get underlying sql.DB: %v", err)
		}
		return sqlDB.Close()
	}
	return nil
}

// GetDB 获取GORM数据库实例
func GetDB() *gorm.DB {
	return DB
}

// AutoMigrate 自动迁移数据库表结构
func AutoMigrate(models ...interface{}) error {
	if DB == nil {
		return fmt.Errorf("database not initialized")
	}
	return DB.AutoMigrate(models...)
}
