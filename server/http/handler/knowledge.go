package handler

import (
    "net/http"
    "path/filepath"
    "strconv"
    "strings"
    "time"

    "gitee.com/openeuler/PilotGo-plugin-llmops/server/service/knowledge"
    "github.com/gin-gonic/gin"
)

func UploadKnowledge(c *gin.Context) {
    object := c.PostForm("object")
    file, header, err := c.Request.FormFile("file")
    if err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": "invalid file"})
        return
    }
    defer file.Close()
    if object == "" {
        object = header.Filename
    }
    if strings.Contains(object, "..") || strings.HasPrefix(object, "/") {
        c.JSON(http.StatusBadRequest, gin.H{"error": "invalid object name"})
        return
    }
    ct := header.Header.Get("Content-Type")
    if ct == "" {
        ct = "application/octet-stream"
    }
    _, err = knowledge.UploadKnowledgeFile(c.Request.Context(), object, file, header.Size, ct)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    c.JSON(http.StatusOK, gin.H{"data": gin.H{"object": object}})
}

func DownloadKnowledge(c *gin.Context) {
    object := c.Query("object")
    if object == "" {
        c.JSON(http.StatusBadRequest, gin.H{"error": "missing object"})
        return
    }
    rc, size, ct, err := knowledge.DownloadKnowledgeFile(c.Request.Context(), object)
    if err != nil {
        c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
        return
    }
    defer rc.Close()
    filename := filepath.Base(object)
    headers := map[string]string{
        "Content-Disposition": "attachment; filename=\"" + filename + "\"",
    }
    c.DataFromReader(http.StatusOK, size, ct, rc, headers)
}

func PresignKnowledge(c *gin.Context) {
    object := c.Query("object")
    if object == "" {
        c.JSON(http.StatusBadRequest, gin.H{"error": "missing object"})
        return
    }
    expiryStr := c.Query("expiry")
    expiry := 3600
    if expiryStr != "" {
        if n, err := strconv.Atoi(expiryStr); err == nil && n > 0 {
            expiry = n
        }
    }
    url, err := knowledge.PresignedDownloadURL(c.Request.Context(), object, time.Duration(expiry)*time.Second)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    c.JSON(http.StatusOK, gin.H{"data": gin.H{"url": url}})
}