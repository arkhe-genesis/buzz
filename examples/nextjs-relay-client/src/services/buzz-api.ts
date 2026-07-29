import api from './api'; // Sua instância Axios base

export const BuzzRestApi = {
  /** Blossom Protocol: Upload de mídia para o S3/MinIO */
  async uploadBlob(file: File): Promise<{ url: string; sha256: string }> {
    const formData = new FormData();
    formData.append('file', file);

    // O cabeçalho Authorization usa o NIP-98 (HTTP Auth Nostr)
    // Em produção, você assina um evento(kind 27235) com a URL e método HTTP
    const response = await api.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  },

  /** Trigger de Workflow Git via REST */
  async triggerGitWorkflow(repoId: string, action: string) {
    return api.post(`/workflow/git/${repoId}`, { action });
  },

  /** Buscar Logs de Auditoria (que o relay escreve no Postgres) */
  async getAuditLogs(params: { limit: number; offset: number }) {
    return api.get('/admin/audit', { params });
  }
};
