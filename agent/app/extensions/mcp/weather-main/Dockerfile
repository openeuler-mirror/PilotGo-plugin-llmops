FROM golang:1.20-alpine AS builder

WORKDIR /app

# Copy go module files first for better layer caching
COPY go.mod ./

# Copy the source code
COPY main.go ./
COPY weather/ ./weather/

# Build the application
RUN go mod download
RUN go build -o weather-app .

# Create a minimal production image
FROM alpine:3.18

WORKDIR /app

# Copy the binary from the builder stage
COPY --from=builder /app/weather-app .

# Expose the application port
EXPOSE 8080

# Set environment variables
ENV PORT=8080

# Run the application
CMD ["./weather-app"]