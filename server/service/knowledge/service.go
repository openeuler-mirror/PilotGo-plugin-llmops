package knowledge

import (
	"context"
	"errors"

	"gitee.com/openeuler/PilotGo-plugin-llmops/server/config"
	"gitee.com/openeuler/PilotGo-plugin-llmops/server/logger"
	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
)

type KnowledgeService struct{}

var (
	globalKnowledgeService *KnowledgeService
)

func GetKnowledgeService() *KnowledgeService {
	if globalKnowledgeService == nil {
		globalKnowledgeService = &KnowledgeService{}
	}
	return globalKnowledgeService
}

func (s *KnowledgeService) Name() string {
	return "Knowledge Service"
}

func (s *KnowledgeService) Run(ctx context.Context) error {
	cfg := config.GetConfig()
	if cfg == nil {
		return errors.New("config not initialized")
	}
	endpoint := cfg.Minio.Endpoint
	accessKey := cfg.Minio.AccessKey
	secretKey := cfg.Minio.SecretKey
	bucket = cfg.Minio.Bucket
	secure := cfg.Minio.UseSSL
	if endpoint == "" || accessKey == "" || secretKey == "" || bucket == "" {
		return errors.New("minio config missing")
	}
	c, err := minio.New(endpoint, &minio.Options{Creds: credentials.NewStaticV4(accessKey, secretKey, ""), Secure: secure})
	if err != nil {
		return err
	}
	mc = c
	exists, err := mc.BucketExists(ctx, bucket)
	if err != nil {
		return err
	}
	if !exists {
		if err := mc.MakeBucket(ctx, bucket, minio.MakeBucketOptions{}); err != nil {
			return err
		}
	}

	<-ctx.Done()
	logger.Infof("service stopped: %s", s.Name())
	return nil
}
