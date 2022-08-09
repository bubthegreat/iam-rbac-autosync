docker build -t "iam-rbac-autosync:0.0.12" .
# minikube image add iam-rbac-autosync:0.0.12  # Local
docker tag "iam-rbac-autosync:0.0.12" "123456789012.dkr.ecr.us-east-1.amazonaws.com/iam-rbac-autosync:0.0.12"
docker push "123456789012.dkr.ecr.us-east-1.amazonaws.com/iam-rbac-autosync:0.0.12"
