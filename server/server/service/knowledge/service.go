package knowledge

import (
	"context"
	"errors"

	"gitee.com/openeuler/PilotGo-plugin-llmops/server/pkg/logger"
	"gitee.com/openeuler/PilotGo-plugin-llmops/server/server/config"
	"gitee.com/openeuler/PilotGo-plugin-llmops/server/server/db"
	"gitee.com/openeuler/PilotGo-plugin-llmops/server/server/service/internal/dao"
	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
)

type KnowledgeService struct {
	kd     *dao.KnowledgeDao
	mc     *minio.Client
	bucket string
}

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

	// init dao and migrate table
	s.kd = dao.NewKnowledgeDao()
	if err := db.AutoMigrate(&dao.Knowledge{}); err != nil {
		return errors.New("failed to migrate knowledge database: " + err.Error())
	}

	endpoint := cfg.Minio.Endpoint
	accessKey := cfg.Minio.AccessKey
	secretKey := cfg.Minio.SecretKey
	s.bucket = cfg.Minio.Bucket
	secure := cfg.Minio.UseSSL
	if endpoint == "" || accessKey == "" || secretKey == "" || s.bucket == "" {
		return errors.New("minio config missing")
	}
	c, err := minio.New(endpoint, &minio.Options{Creds: credentials.NewStaticV4(accessKey, secretKey, ""), Secure: secure})
	if err != nil {
		return err
	}
	s.mc = c
	exists, err := s.mc.BucketExists(ctx, s.bucket)
	if err != nil {
		return err
	}
	if !exists {
		if err := s.mc.MakeBucket(ctx, s.bucket, minio.MakeBucketOptions{}); err != nil {
			return err
		}
	}

	<-ctx.Done()
	logger.Infof("service stopped: %s", s.Name())
	return nil
}
