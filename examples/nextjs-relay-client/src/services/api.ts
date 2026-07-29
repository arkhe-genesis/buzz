const api = {
    post: async (url: string, data?: any, config?: any) => ({ data: { url: '', sha256: '' } }),
    get: async (url: string, config?: any) => ({ data: [] })
};

export default api;
