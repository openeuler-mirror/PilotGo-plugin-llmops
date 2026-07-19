package knowledge

import (
	"context"
	"errors"
	"io"
	"time"

	"gitee.com/openeuler/PilotGo-plugin-llmops/server/server/service/internal/dao"
	"github.com/minio/minio-go/v7"
)

type KnowledgeDTO struct {
	ID        int64  `json:"id"`
	ProjectID int    `json:"project_id"`
	Object    string `json:"object"`
	FileName  string `json:"file_name"`
	Uploader  string `json:"uploader"`
	Desc      string `json:"desc"`
	CreatedAt string `json:"created_at"`
	UpdatedAt string `json:"updated_at"`
}

// ListKnowledge 获取知识文件列表，projectID > 0 时按项目过滤
func (s *KnowledgeService) ListKnowledge(projectID int) ([]*KnowledgeDTO, error) {
	if s.kd == nil {
		return nil, errors.New("knowledge service not initialized")
	}

	var items []*dao.Knowledge
	var err error
	if projectID > 0 {
		items, err = s.kd.ListByProjectID(projectID)
	} else {
		items, err = s.kd.List()
	}
	if err != nil {
		return nil, err
	}

	// 转换为DTO列表
	result := make([]*KnowledgeDTO, len(items))
	for i, item := range items {
		result[i] = &KnowledgeDTO{
			ID:        item.ID,
			ProjectID: item.ProjectID,
			Object:    item.Object,
			FileName:  item.FileName,
			Uploader:  item.Uploader,
			Desc:      item.Desc,
			CreatedAt: item.CreatedAt,
			UpdatedAt: item.UpdatedAt,
		}
	}

	return result, nil
}

type UploadKnowledgeReq struct {
	ProjectID int    `json:"project_id"`
	Object    string `json:"object"`
	FileName  string `json:"file_name"`
	Uploader  string `json:"uploader"`
	Desc      string `json:"desc"`
}

func (s *KnowledgeService) UploadKnowledgeFile(ctx context.Context, req UploadKnowledgeReq, r io.Reader, size int64, contentType string) (string, error) {
	if s.mc == nil || s.bucket == "" || s.kd == nil {
		return "", errors.New("knowledge service not initialized")
	}
	obj := req.Object
	if obj == "" {
		obj = req.FileName
	}
	if obj == "" {
		return "", errors.New("invalid object name")
	}
	_, err := s.mc.PutObject(ctx, s.bucket, obj, r, size, minio.PutObjectOptions{ContentType: contentType})
	if err != nil {
		return "", err
	}
	now := time.Now().Format("2006-01-02 15:04:05")
	k := &dao.Knowledge{
		ProjectID: req.ProjectID,
		Object:    obj,
		FileName:  req.FileName,
		Uploader:  req.Uploader,
		Desc:      req.Desc,
		CreatedAt: now,
		UpdatedAt: now,
	}
	if err := s.kd.Create(k); err != nil {
		return "", err
	}
	return obj, nil
}

func (s *KnowledgeService) DownloadKnowledgeFile(ctx context.Context, objectName string) (io.ReadCloser, int64, string, error) {
	if s.mc == nil || s.bucket == "" {
		return nil, 0, "", errors.New("knowledge service not initialized")
	}
	obj, err := s.mc.GetObject(ctx, s.bucket, objectName, minio.GetObjectOptions{})
	if err != nil {
		return nil, 0, "", err
	}
	info, err := s.mc.StatObject(ctx, s.bucket, objectName, minio.StatObjectOptions{})
	if err != nil {
		obj.Close()
		return nil, 0, "", err
	}
	return obj, info.Size, info.ContentType, nil
}

func (s *KnowledgeService) PresignedDownloadURL(ctx context.Context, objectName string, expiry time.Duration) (string, error) {
	if s.mc == nil || s.bucket == "" {
		return "", errors.New("knowledge service not initialized")
	}
	u, err := s.mc.PresignedGetObject(ctx, s.bucket, objectName, expiry, nil)
	if err != nil {
		return "", err
	}
	return u.String(), nil
}

func (s *KnowledgeService) DeleteKnowledge(ctx context.Context, id int64) error {
	if s.mc == nil || s.bucket == "" || s.kd == nil {
		return errors.New("knowledge service not initialized")
	}
	k, err := s.kd.GetByID(id)
	if err != nil {
		return err
	}
	if err := s.mc.RemoveObject(ctx, s.bucket, k.Object, minio.RemoveObjectOptions{}); err != nil {
		return err
	}
	return s.kd.Delete(id)
}
