package knowledge

import (
	"context"
	"errors"
	"io"
	"time"

	"github.com/minio/minio-go/v7"
)

var (
	mc     *minio.Client
	bucket string
)

func UploadKnowledgeFile(ctx context.Context, objectName string, r io.Reader, size int64, contentType string) (string, error) {
	if mc == nil || bucket == "" {
		return "", errors.New("knowledge service not initialized")
	}
	_, err := mc.PutObject(ctx, bucket, objectName, r, size, minio.PutObjectOptions{ContentType: contentType})
	if err != nil {
		return "", err
	}
	return objectName, nil
}

func DownloadKnowledgeFile(ctx context.Context, objectName string) (io.ReadCloser, int64, string, error) {
	if mc == nil || bucket == "" {
		return nil, 0, "", errors.New("knowledge service not initialized")
	}
	obj, err := mc.GetObject(ctx, bucket, objectName, minio.GetObjectOptions{})
	if err != nil {
		return nil, 0, "", err
	}
	info, err := mc.StatObject(ctx, bucket, objectName, minio.StatObjectOptions{})
	if err != nil {
		obj.Close()
		return nil, 0, "", err
	}
	return obj, info.Size, info.ContentType, nil
}

func PresignedDownloadURL(ctx context.Context, objectName string, expiry time.Duration) (string, error) {
	if mc == nil || bucket == "" {
		return "", errors.New("knowledge service not initialized")
	}
	u, err := mc.PresignedGetObject(ctx, bucket, objectName, expiry, nil)
	if err != nil {
		return "", err
	}
	return u.String(), nil
}
