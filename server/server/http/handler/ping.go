package handler

import (
	"github.com/gin-gonic/gin"
)

// Ping 用于健康检查
func Ping(c *gin.Context) {
	ResponseOK(c, "pong")
}
