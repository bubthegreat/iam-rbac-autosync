# IAM RBAC Autoupdater

This operator will reach out to monitor our IAM groups (Listed in the custom resource) and apply those changes to the appropriate namespaces.  This is pretty rough with documentation because it's too specific to our use case, but I'd like to solicit some feedback on the structure and scope that others would need and begin to update this to reflect a more general use case that would help others keep their configmaps up to date automatically for AWS auth.

NOTE: This is really only useful if you need to have roles associated with specific namespaces through RBAC - if you're just willy nilly giving admin to everyone like cluster role level, this won't be useful for you.  If you have a namespace specific binding you want to autosync then this is for you.

An example CRD: 

```
apiVersion: iamrbacautoupdater.com/v1
kind: IAMRBACMapper
metadata:
  name: iam-rbac-autosync-prod
  namespace: devops-iam-rbac-autosync
spec:
  targetIAMGroup: my-iam-group
  targetRBACGroup: my-rbac-group
  protectedNamespaces:
    - prod
    - preprod
```

This will reach out to the iam group `my-iam-group` and associate any users within it to the target rbac group `my-rbac-group`, and will ensure the protected namespaces `prod` and `preprod` are permitted for use by `my-rbac-group`.  Users that are not in the RBAC group are created - users that are no longer in the RBAC group are removed from the rbac group permissions.

## Build
NOTE: You must be logged in to the AWS CLI or run this from jenkins that already has the permissions to run the ECR login

```
(aws-cli) [bub@bub iam-rbac-operator (⎈|test-eks:test1)]$ ./build.sh
[+] Building 5.8s (9/9) FINISHED
 => [internal] load build definition from Dockerfile                                                                        0.1s
 => => transferring dockerfile: 38B                                                                                         0.0s
 => [internal] load .dockerignore                                                                                           0.1s
 => => transferring context: 2B                                                                                             0.0s
 => [internal] load metadata for docker.io/library/python:3.7                                                               5.0s
 => [internal] load build context                                                                                           0.1s
 => => transferring context: 8.73kB                                                                                         0.0s
 => [1/4] FROM docker.io/library/python:3.7@sha256:243d808efa708d54e461742bee944c17a586042488e98403ebf13b18e7a1bea1         0.0s
 => CACHED [2/4] ADD ./requirements.txt requirements.txt                                                                    0.0s
 => CACHED [3/4] RUN pip install -r requirements.txt                                                                        0.0s
 => [4/4] ADD ./src /src                                                                                                    0.1s
 => exporting to image                                                                                                      0.2s
 => => exporting layers                                                                                                     0.1s
 => => writing image sha256:de53a3e8de6d5fa7f0b27ec8840a0d846294ff4af17989914e1c43fa435ee98f                                                    0.0s
 => => naming to docker.io/library/iam-rbac-autosync:0.0.12                                                                   0.0s
The push refers to repository [123456789012.dkr.ecr.us-east-1.amazonaws.com/iam-rbac-autosync]
ae83f34caeda: Pushed
10371bd12b0f: Layer already exists
df30961ede71: Layer already exists
6dddb432194c: Layer already exists
5f71c8685acb: Layer already exists
583a78313b06: Layer already exists
2143381c9922: Layer already exists
12228ba7a3b1: Layer already exists
9b55156abf26: Layer already exists
293d5db30c9f: Layer already exists
03127cdb479b: Layer already exists
9c742cd6c7a5: Layer already exists
0.0.10: digest: sha256:52db703b326453eae1834c811944428cc98c927067c20b1b4f0015ec27209ae2 size: 2846
(aws-cli) [bub@bub iam-rbac-operator (⎈|test-eks:test1)]$
```

## Deploy

```
(aws-cli) [bub@bub iam-rbac-operator (⎈|test-eks:test1)]$ kubectl apply -f deployment/
namespace/devops-iam-rbac-autosyncs unchanged
deployment.apps/iam-rbac-autosync-operator configured
serviceaccount/iam-rbac-autosync-account unchanged
clusterrole.rbac.authorization.k8s.io/iam-rbac-autosync-role-cluster unchanged
role.rbac.authorization.k8s.io/iam-rbac-autosync-role-namespaced unchanged
clusterrolebinding.rbac.authorization.k8s.io/iam-rbac-autosync-rolebinding-cluster unchanged
rolebinding.rbac.authorization.k8s.io/iam-rbac-autosync-rolebinding-namespaced unchanged
(aws-cli) [bub@bub iam-rbac-operator (⎈|test-eks:test1)]$
```


## Check how it's working

Verify that you have custom resources deployed:

``` 
(aws-cli) bub@bub:~/iam-rbac-autosync$ kubectl get iam-rbac-autosyncs
NAME                   AGE
iam-rbac-autosync-dev    12s
(aws-cli) bub@bub:~/iam-rbac-autosync$ 
```

Check that you have a pod running: 

```
(aws-cli) bub@bub:~/iam-rbac-autosync$ kubectl get pods -n iam-rbac-autosyncs
NAME                                       READY   STATUS    RESTARTS   AGE
iam-rbac-autosync-operator-65f675766-krzh8   1/1     Running   0          55s
(aws-cli) bub@bub:~/iam-rbac-autosync$
```

View/tail logs for the pod

```
(aws-cli) [bub@bub iam-rbac-operator (⎈|test-eks:devops-iam-rbac-autosyncs)]$ kubectl logs -f `kubectl get pods -n devops-iam-rbac-autosyncs | grep iam-rbac-autosync-operator | awk '{print $1}'` -n devops-iam-rbac-autosyncs
/usr/local/lib/python3.7/site-packages/kopf/_core/reactor/running.py:178: FutureWarning: Absence of either namespaces or cluster-wide flag will become an error soon. For now, switching to the cluster-wide mode for backward compatibility.
  FutureWarning)
[2022-08-03 21:14:59,653] kopf._core.engines.a [INFO    ] Initial authentication has been initiated.
[2022-08-03 21:14:59,656] kopf.activities.auth [INFO    ] Activity 'login_via_client' succeeded.
[2022-08-03 21:14:59,656] kopf._core.engines.a [INFO    ] Initial authentication has finished.
[2022-08-03 21:15:00,437] iam-rbac-autosyncs-log [INFO    ] IAM group eks-devops found.
[2022-08-03 21:15:00,565] iam-rbac-autosyncs-log [INFO    ] IAM group eks-admins found.
[2022-08-03 21:15:00,627] iam-rbac-autosyncs-log [INFO    ] IAM group eks-developers found.
[2022-08-03 21:15:00,688] iam-rbac-autosyncs-log [INFO    ] IAM group eks-developers found.
[2022-08-03 21:15:00,735] iam-rbac-autosyncs-log [INFO    ] No changes detected in group membership
[2022-08-03 21:15:00,736] kopf.objects         [INFO    ] [iam-rbac-autosync-dev] Timer 'update_rbac_with_iam_changes' succeeded.
[2022-08-03 21:15:30,829] iam-rbac-autosyncs-log [INFO    ] IAM group eks-devops found.
[2022-08-03 21:15:30,888] iam-rbac-autosyncs-log [INFO    ] IAM group eks-admins found.
[2022-08-03 21:15:30,994] iam-rbac-autosyncs-log [INFO    ] IAM group eks-developers found.
[2022-08-03 21:15:31,104] iam-rbac-autosyncs-log [INFO    ] IAM group eks-developers found.
[2022-08-03 21:15:31,122] iam-rbac-autosyncs-log [INFO    ] No changes detected in group membership
[2022-08-03 21:15:31,124] kopf.objects         [INFO    ] [iam-rbac-autosync-dev] Timer 'update_rbac_with_iam_changes' succeeded.
[2022-08-03 21:16:01,242] iam-rbac-autosyncs-log [INFO    ] IAM group eks-devops found.
[2022-08-03 21:16:01,301] iam-rbac-autosyncs-log [INFO    ] IAM group eks-admins found.
[2022-08-03 21:16:01,395] iam-rbac-autosyncs-log [INFO    ] IAM group eks-developers found.
[2022-08-03 21:16:01,518] iam-rbac-autosyncs-log [INFO    ] IAM group eks-developers found.
[2022-08-03 21:16:01,537] iam-rbac-autosyncs-log [INFO    ] No changes detected in group membership

```
