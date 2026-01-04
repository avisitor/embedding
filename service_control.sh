#!/bin/bash
# Hawaiian Corpus Embedding Service Control Script

SERVICE_NAME="hawaiian-embedding"

show_help() {
    echo "Hawaiian Corpus Embedding Service Control"
    echo "Usage: $0 {start|stop|restart|status|logs|health}"
    echo ""
    echo "Commands:"
    echo "  start    - Start the embedding service"
    echo "  stop     - Stop the embedding service gracefully"
    echo "  restart  - Restart the embedding service"
    echo "  status   - Show service status"
    echo "  logs     - Show service logs (last 20 lines)"
    echo "  health   - Test service health endpoint"
    echo "  enable   - Enable service to start on boot"
    echo "  disable  - Disable service from starting on boot"
}

case "$1" in
    start)
        echo "🚀 Starting Hawaiian Embedding Service..."
        sudo systemctl start $SERVICE_NAME.service
        sleep 3
        sudo systemctl status $SERVICE_NAME.service --no-pager
        ;;
    stop)
        echo "🛑 Stopping Hawaiian Embedding Service..."
        sudo systemctl stop $SERVICE_NAME.service
        echo "✅ Service stopped"
        ;;
    restart)
        echo "🔄 Restarting Hawaiian Embedding Service..."
        sudo systemctl restart $SERVICE_NAME.service
        sleep 3
        sudo systemctl status $SERVICE_NAME.service --no-pager
        ;;
    status)
        sudo systemctl status $SERVICE_NAME.service --no-pager
        ;;
    logs)
        echo "📋 Recent service logs:"
        sudo journalctl -u $SERVICE_NAME.service -n 20 --no-pager
        ;;
    health)
        echo "🏥 Testing service health..."
        if curl -s http://localhost:5000/health > /dev/null; then
            echo "✅ Service is healthy"
            curl -s http://localhost:5000/health | python3 -m json.tool
        else
            echo "❌ Service health check failed"
        fi
        ;;
    enable)
        echo "⚡ Enabling service to start on boot..."
        sudo systemctl enable $SERVICE_NAME.service
        echo "✅ Service enabled"
        ;;
    disable)
        echo "🔌 Disabling service from starting on boot..."
        sudo systemctl disable $SERVICE_NAME.service
        echo "✅ Service disabled"
        ;;
    *)
        show_help
        exit 1
        ;;
esac
