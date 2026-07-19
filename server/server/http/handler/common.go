package handler

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

func ResponseOK(c *gin.Context, msg string) {
	c.JSON(http.StatusOK, gin.H{
		"message": msg,
	})
}

func Response(c *gin.Context, data interface{}) {
	c.JSON(http.StatusOK, gin.H{
		"data": data,
	})
}

func ResponsePage(c *gin.Context, page, perPage, total int, data interface{}) {
	c.JSON(http.StatusOK, gin.H{
		"page":    page,
		"perpage": perPage,
		"total":   total,
		"data":    data,
	})
}

func ResponseError(c *gin.Context, code int, err string) {
	c.JSON(code, gin.H{
		"error": err,
	})
}
