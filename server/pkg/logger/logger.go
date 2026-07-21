package logger

import (
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"runtime"
)

type LoggerConfig struct {
	Level string `yaml:"level"`
}

var global_logger *slog.Logger

func parseLogLevel(level string) slog.Level {
	switch level {
	case "debug":
		return slog.LevelDebug
	case "info":
		return slog.LevelInfo
	case "warn":
		return slog.LevelWarn
	case "error":
		return slog.LevelError
	default:
		return slog.LevelInfo
	}
}

func Init(cfg *LoggerConfig) {
	// 创建带有源码位置信息的日志选项
	_, file, _, _ := runtime.Caller(0)
	// 获取logger包所在目录
	loggerDir := filepath.Dir(file)
	// 获取项目根目录（logger包的上一级目录）
	projectRoot := filepath.Dir(filepath.Dir(loggerDir))
	opts := &slog.HandlerOptions{
		Level:     parseLogLevel(cfg.Level), // 设置日志级别
		AddSource: true,                     // 添加文件和行号信息
		ReplaceAttr: func(groups []string, a slog.Attr) slog.Attr {
			// 处理source字段，将绝对路径转换为相对路径
			if a.Key == "source" {
				if source, ok := a.Value.Any().(*slog.Source); ok {
					// 获取上一级调用者的代码行信息
					if _, file, line, ok := runtime.Caller(7); ok {
						// 使用init中获取的项目根目录路径
						if rel, err := filepath.Rel(projectRoot, file); err == nil {
							source.File = " " + rel
							source.Line = line
						}
					}
				}
			}
			return a
		},
	}

	// 创建文本格式的处理器
	handler := slog.NewTextHandler(os.Stdout, opts)

	// 如果需要JSON格式，可以使用：
	// handler := slog.NewJSONHandler(os.Stdout, opts)

	global_logger = slog.New(handler)

	// 设置为默认日志器
	slog.SetDefault(global_logger)
}

// 便捷方法
func Debug(msg string, args ...any) {
	global_logger.Debug(msg, args...)
}

func Debugf(format string, args ...any) {
	global_logger.Debug(fmt.Sprintf(format, args...))
}

func Info(msg string, args ...any) {
	global_logger.Info(msg, args...)
}

func Infof(format string, args ...any) {
	global_logger.Info(fmt.Sprintf(format, args...))
}

func Warn(msg string, args ...any) {
	global_logger.Warn(msg, args...)
}

func Warnf(format string, args ...any) {
	global_logger.Warn(fmt.Sprintf(format, args...))
}

func Error(msg string, args ...any) {
	global_logger.Error(msg, args...)
}

func Errorf(format string, args ...any) {
	global_logger.Error(fmt.Sprintf(format, args...))
}

func Fatal(msg string, args ...any) {
	global_logger.Error(msg, args...)
	os.Exit(1)
}

func Fatalf(format string, args ...any) {
	global_logger.Error(fmt.Sprintf(format, args...))
	os.Exit(1)
}
