const axios = require('axios');

class MediaDL {
    constructor(config = {}) {
        this.apiUrl = config.apiUrl || 'http://localhost:8000';
    }

    async createJob(payload) {
        const response = await axios.post(`${this.apiUrl}/jobs`, payload);
        return response.data;
    }

    async getJobStatus(jobId) {
        const response = await axios.get(`${this.apiUrl}/jobs/${jobId}`);
        return response.data;
    }
    
    async batchConvert(inputs, outputFormat, webhookUrl = null) {
        const jobIds = [];
        for (const input of inputs) {
            const payload = { type: 'convert', input, outputFormat };
            if (webhookUrl) payload.webhookUrl = webhookUrl;
            
            const res = await this.createJob(payload);
            jobIds.push(res.jobId);
        }
        return jobIds;
    }

    waitForCompletion(jobId, intervalMs = 5000) {
        return new Promise((resolve, reject) => {
            const timer = setInterval(async () => {
                try {
                    const status = await this.getJobStatus(jobId);
                    if (status.status === 'completed') {
                        clearInterval(timer);
                        resolve(status);
                    } else if (status.status === 'failed') {
                        clearInterval(timer);
                        reject(new Error(`Job failed: ${status.error}`));
                    }
                } catch (e) {
                    clearInterval(timer);
                    reject(e);
                }
            }, intervalMs);
        });
    }
}

module.exports = { MediaDL };
