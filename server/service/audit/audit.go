package audit

import (
	"context"
	"errors"
	"time"

	"gitee.com/openeuler/PilotGo-plugin-llmops/server/service/internal/dao"
)

type CreateAuditReq struct {
	// ProjectID 项目ID
	ProjectID int
	// Actor 操作人
	Actor string
	// Target 操作目标
	Target string
	// ActionType 操作类型
	ActionType string
	// Action 操作说明
	Action string
	// Result 操作结果
	Result string
}

func (s *AuditService) AddAuditRecord(ctx context.Context, req CreateAuditReq) (int64, error) {
	if s.ad == nil {
		return 0, errors.New("audit service not initialized")
	}
	now := time.Now().Format("2006-01-02 15:04:05")
	a := &dao.Audit{
		ProjectID:  req.ProjectID,
		Actor:      req.Actor,
		ActionType: req.ActionType,
		Action:     req.Action,
		Target:     req.Target,
		Result:     req.Result,
		CreatedAt:  now,
	}
	if err := s.ad.Create(a); err != nil {
		return 0, err
	}
	return a.ID, nil
}

type ListAuditReq struct {
	ProjectID  *int
	Actor      string
	ActionType string
	Target     string
}

func (s *AuditService) ListAuditsByFilters(ctx context.Context, req *ListAuditReq) ([]*dao.Audit, error) {
	if s.ad == nil {
		return nil, errors.New("audit service not initialized")
	}
	var q *dao.AuditQuery
	if req != nil {
		q = &dao.AuditQuery{
			ProjectID:  req.ProjectID,
			Actor:      req.Actor,
			ActionType: req.ActionType,
			Target:     req.Target,
		}
	}
	return s.ad.ListByQuery(q)
}

func (s *AuditService) GetAuditByID(ctx context.Context, id int64) (*dao.Audit, error) {
	if s.ad == nil {
		return nil, errors.New("audit service not initialized")
	}
	return s.ad.GetByID(id)
}

func (s *AuditService) ListAudits(ctx context.Context) ([]*dao.Audit, error) {
	if s.ad == nil {
		return nil, errors.New("audit service not initialized")
	}
	return s.ad.List()
}

func (s *AuditService) ListAuditsByProjectID(ctx context.Context, projectID int) ([]*dao.Audit, error) {
	if s.ad == nil {
		return nil, errors.New("audit service not initialized")
	}
	return s.ad.ListByProjectID(projectID)
}

func (s *AuditService) ListAuditsByProjectIDPaged(ctx context.Context, projectID, page, perPage int) (items []*dao.Audit, total int64, err error) {
	if s.ad == nil {
		return nil, 0, errors.New("audit service not initialized")
	}
	q := &dao.AuditQuery{
		ProjectID: &projectID,
		Limit:     perPage,
		Offset:    (page - 1) * perPage,
	}
	total, err = s.ad.CountByQuery(q)
	if err != nil {
		return nil, 0, err
	}
	items, err = s.ad.ListByQuery(q)
	if err != nil {
		return nil, 0, err
	}
	return items, total, nil
}
