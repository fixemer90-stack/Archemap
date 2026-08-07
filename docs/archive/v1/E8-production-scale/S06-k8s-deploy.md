# Story E8.S06: K8s Deploy

**Feature:** [Production & Scale](Archemap/docs/features/v1/E8-production-scale/FEATURE.md)
**Статус:** ⬜ Не начато

## Контекст

Деплой на Kubernetes (Yandex Managed Kubernetes) с autoscaling и rolling updates.

## Что сделать

- Написать K8s manifests (Deployment, Service, Ingress, ConfigMap, Secret)
- Настроить Yandex Managed Kubernetes
- Autoscaling (HPA)
- Rolling updates
- Health checks (readiness/liveness)
- Resource limits

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `infra/k8s/` | K8s manifests |
| `infra/k8s/backend/` | Backend deployment |
| `infra/k8s/frontend/` | Frontend deployment |
| `infra/k8s/postgres/` | PostgreSQL StatefulSet |
| `infra/k8s/redis/` | Redis StatefulSet |
| `infra/k8s/ingress/` | Ingress configuration |

## K8s Resources

### Backend Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: astrotype-backend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  template:
    spec:
      containers:
        - name: backend
          image: cr.yandex/astrotype/backend:latest
          ports:
            - containerPort: 8000
          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
          readinessProbe:
            httpGet:
              path: /api/v1/health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /api/v1/health
              port: 8000
            initialDelaySeconds: 15
            periodSeconds: 20
```

### HPA (Horizontal Pod Autoscaler)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: astrotype-backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

## Критерии приёмки

- [ ] K8s manifests для всех сервисов
- [ ] Yandex Managed Kubernetes cluster создан
- [ ] Backend: 2+ replicas, HPA
- [ ] Frontend: 2+ replicas
- [ ] PostgreSQL: StatefulSet с persistent volume
- [ ] Redis: StatefulSet
- [ ] Ingress с TLS
- [ ] Health checks (readiness + liveness)
- [ ] Resource limits
- [ ] Rolling updates без downtime

## Примечания

- Yandex Managed Kubernetes (если деплой на Yandex Cloud)
- Альтернатива: GKE, EKS, AKS
- Для начала: 2 replicas, потом autoscaling
