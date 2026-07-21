package handler

import (
	"net/http"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"gitee.com/openeuler/PilotGo-plugin-llmops/server/server/service/knowledge"
	"github.com/gin-gonic/gin"
)

func ListKnowledge(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.Atoi(idStr)
	if err != nil || id <= 0 {
		ResponseError(c, http.StatusBadRequest, "invalid project id")
		return
	}
	data, err := knowledge.GetKnowledgeService().ListKnowledge(id)
	if err != nil {
		ResponseError(c, http.StatusInternalServerError, err.Error())
		return
	}
	Response(c, data)
}

func UploadKnowledge(c *gin.Context) {
	object := c.PostForm("object")
	projectIDStr := c.PostForm("project_id")
	uploader := c.PostForm("uploader")
	desc := c.PostForm("desc")

	var projectID int
	if projectIDStr != "" {
		if n, err := strconv.Atoi(projectIDStr); err == nil && n > 0 {
			projectID = n
		} else {
			ResponseError(c, http.StatusBadRequest, "invalid project_id")
			return
		}
	} else {
		ResponseError(c, http.StatusBadRequest, "missing project_id")
		return
	}

	file, header, err := c.Request.FormFile("file")
	if err != nil {
		ResponseError(c, http.StatusBadRequest, "invalid file")
		return
	}
	defer file.Close()
	if object == "" {
		object = header.Filename
	}
	if strings.Contains(object, "..") || strings.HasPrefix(object, "/") {
		ResponseError(c, http.StatusBadRequest, "invalid object name")
		return
	}
	ct := header.Header.Get("Content-Type")
	if ct == "" {
		ct = "application/octet-stream"
	}
	req := knowledge.UploadKnowledgeReq{
		ProjectID: projectID,
		Object:    object,
		FileName:  header.Filename,
		Uploader:  uploader,
		Desc:      desc,
	}
	_, err = knowledge.GetKnowledgeService().UploadKnowledgeFile(c.Request.Context(), req, file, header.Size, ct)
	if err != nil {
		ResponseError(c, http.StatusInternalServerError, err.Error())
		return
	}
	Response(c, gin.H{"object": object})
}

func DownloadKnowledge(c *gin.Context) {
	object := c.Query("object")
	if object == "" {
		ResponseError(c, http.StatusBadRequest, "missing object")
		return
	}
	rc, size, ct, err := knowledge.GetKnowledgeService().DownloadKnowledgeFile(c.Request.Context(), object)
	if err != nil {
		ResponseError(c, http.StatusNotFound, err.Error())
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
		ResponseError(c, http.StatusBadRequest, "missing object")
		return
	}
	expiryStr := c.Query("expiry")
	expiry := 3600
	if expiryStr != "" {
		if n, err := strconv.Atoi(expiryStr); err == nil && n > 0 {
			expiry = n
		}
	}
	url, err := knowledge.GetKnowledgeService().PresignedDownloadURL(c.Request.Context(), object, time.Duration(expiry)*time.Second)
	if err != nil {
		ResponseError(c, http.StatusInternalServerError, err.Error())
		return
	}
	Response(c, gin.H{"url": url})
}

func DeleteKnowledge(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil || id <= 0 {
		ResponseError(c, http.StatusBadRequest, "invalid id")
		return
	}
	if err := knowledge.GetKnowledgeService().DeleteKnowledge(c.Request.Context(), id); err != nil {
		ResponseError(c, http.StatusInternalServerError, err.Error())
		return
	}
	ResponseOK(c, "deleted")
}
