package com.mediadl;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;

public class MediaDLClient {

    private final String apiUrl;
    private final HttpClient httpClient;
    private final ObjectMapper mapper;

    public MediaDLClient(String apiUrl) {
        this.apiUrl = apiUrl != null && !apiUrl.isEmpty() ? apiUrl : "http://localhost:8000";
        this.httpClient = HttpClient.newHttpClient();
        this.mapper = new ObjectMapper();
    }

    public MediaDLClient() {
        this(null);
    }

    public String convert(String inputUri, String format, String webhookUrl) throws Exception {
        ObjectNode payload = mapper.createObjectNode();
        payload.put("type", "convert");
        payload.put("input", inputUri);
        payload.put("outputFormat", format);
        if (webhookUrl != null) payload.put("webhookUrl", webhookUrl);

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(this.apiUrl + "/jobs"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(payload.toString()))
                .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        return mapper.readTree(response.body()).get("jobId").asText();
    }

    public String status(String jobId) throws Exception {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(this.apiUrl + "/jobs/" + jobId))
                .GET()
                .build();
        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        return response.body();
    }
    
    // Quick Batch Helper
    public List<String> convertBatch(List<String> inputs, String format) throws Exception {
        List<String> ids = new ArrayList<>();
        for(String in : inputs) {
            ids.add(convert(in, format, null));
        }
        return ids;
    }
}
