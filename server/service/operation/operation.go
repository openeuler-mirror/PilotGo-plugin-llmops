package operation

import (
	"errors"

	"gitee.com/openeuler/PilotGo-plugin-llmops/server/service/internal/dao"
)

type OperationScriptDTO struct {
	ID          int64  `json:"id"`
	ProjectID   int    `json:"project_id"`
	Name        string `json:"name"`
	Description string `json:"description"`
	Content     string `json:"content"`
	UpdatedBy   string `json:"updated_by"`
	CreatedAt   string `json:"created_at"`
	UpdatedAt   string `json:"updated_at"`
}

func toOperationScriptDTO(s *dao.OperationScript) *OperationScriptDTO {
	return &OperationScriptDTO{
		ID:          s.ID,
		ProjectID:   s.ProjectID,
		Name:        s.Name,
		Description: s.Description,
		Content:     s.Content,
		UpdatedBy:   s.UpdatedBy,
		CreatedAt:   s.CreatedAt,
		UpdatedAt:   s.UpdatedAt,
	}
}

func (s *OperationService) List(projectID int) ([]*OperationScriptDTO, error) {
	if s.od == nil {
		return nil, errors.New("operation service not initialized")
	}
	items, err := s.od.ListByProjectID(projectID)
	if err != nil {
		return nil, err
	}
	dtos := make([]*OperationScriptDTO, 0, len(items))
	for _, item := range items {
		dtos = append(dtos, toOperationScriptDTO(item))
	}
	return dtos, nil
}

func (s *OperationService) Create(projectID int, name, description, content, updatedBy string) error {
	if s.od == nil {
		return errors.New("operation service not initialized")
	}
	if name == "" {
		return errors.New("script name cannot be empty")
	}
	script := &dao.OperationScript{
		ProjectID:   projectID,
		Name:        name,
		Description: description,
		Content:     content,
		UpdatedBy:   updatedBy,
	}
	return s.od.Create(script)
}

func (s *OperationService) Update(id int64, name, description, content, updatedBy string) error {
	if s.od == nil {
		return errors.New("operation service not initialized")
	}
	if id <= 0 {
		return errors.New("invalid id")
	}
	if name == "" {
		return errors.New("script name cannot be empty")
	}
	script := &dao.OperationScript{
		ID:          id,
		Name:        name,
		Description: description,
		Content:     content,
		UpdatedBy:   updatedBy,
	}
	return s.od.Update(script)
}

func (s *OperationService) Delete(id int64) error {
	if s.od == nil {
		return errors.New("operation service not initialized")
	}
	if id <= 0 {
		return errors.New("invalid id")
	}
	return s.od.Delete(id)
}
