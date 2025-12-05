"""Kubernetes Deployment resources"""
import pulumi
import pulumi_kubernetes as k8s


def create_deployment_with_gcp_creds(
    provider: k8s.Provider,
    namespace: k8s.core.v1.Namespace,
    config_map: k8s.core.v1.ConfigMap,
    secret: k8s.core.v1.Secret,
    name: str,
    image: str,
    port: int,
    replicas: int = 2,
    cpu_request: str = "250m",
    memory_request: str = "512Mi",
    cpu_limit: str = "1000m",
    memory_limit: str = "2Gi",
):
    """Create deployment with GCP credentials mounted"""
    
    return k8s.apps.v1.Deployment(
        f"{name}-deployment",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name=name,
            namespace=namespace.metadata.name,
            labels={"app": name}
        ),
        spec=k8s.apps.v1.DeploymentSpecArgs(
            replicas=replicas,
            selector=k8s.meta.v1.LabelSelectorArgs(
                match_labels={"app": name}
            ),
            template=k8s.core.v1.PodTemplateSpecArgs(
                metadata=k8s.meta.v1.ObjectMetaArgs(
                    labels={"app": name}
                ),
                spec=k8s.core.v1.PodSpecArgs(
                    containers=[k8s.core.v1.ContainerArgs(
                        name=name,
                        image=image,
                        ports=[k8s.core.v1.ContainerPortArgs(
                            container_port=port,
                            name="http"
                        )],
                        env=[
                            k8s.core.v1.EnvVarArgs(name="PORT", value=str(port)),
                            k8s.core.v1.EnvVarArgs(
                                name="GOOGLE_APPLICATION_CREDENTIALS",
                                value="/secrets/gcp/key.json"
                            ),
                        ],
                        env_from=[
                            k8s.core.v1.EnvFromSourceArgs(
                                config_map_ref=k8s.core.v1.ConfigMapEnvSourceArgs(
                                    name=config_map.metadata.name
                                )
                            ),
                        ],
                        resources=k8s.core.v1.ResourceRequirementsArgs(
                            requests={"cpu": cpu_request, "memory": memory_request},
                            limits={"cpu": cpu_limit, "memory": memory_limit}
                        ),
                        liveness_probe=k8s.core.v1.ProbeArgs(
                            http_get=k8s.core.v1.HTTPGetActionArgs(
                                path="/health",
                                port=port
                            ),
                            initial_delay_seconds=30,
                            period_seconds=10,
                        ),
                        readiness_probe=k8s.core.v1.ProbeArgs(
                            http_get=k8s.core.v1.HTTPGetActionArgs(
                                path="/health",
                                port=port
                            ),
                            initial_delay_seconds=5,
                            period_seconds=5,
                        ),
                        volume_mounts=[
                            k8s.core.v1.VolumeMountArgs(
                                name="gcp-credentials",
                                mount_path="/secrets/gcp",
                                read_only=True
                            )
                        ]
                    )],
                    volumes=[
                        k8s.core.v1.VolumeArgs(
                            name="gcp-credentials",
                            secret=k8s.core.v1.SecretVolumeSourceArgs(
                                secret_name=secret.metadata.name,
                                items=[k8s.core.v1.KeyToPathArgs(
                                    key="gcp-key.json",
                                    path="key.json"
                                )]
                            )
                        )
                    ]
                )
            )
        ),
        opts=pulumi.ResourceOptions(
            provider=provider,
            depends_on=[namespace, config_map, secret]
        )
    )


def create_deployment_basic(
    provider: k8s.Provider,
    namespace: k8s.core.v1.Namespace,
    config_map: k8s.core.v1.ConfigMap,
    name: str,
    image: str,
    port: int,
    replicas: int = 2,
    cpu_request: str = "250m",
    memory_request: str = "512Mi",
    cpu_limit: str = "1000m",
    memory_limit: str = "2Gi",
):
    """Create basic deployment without GCP credentials"""
    
    return k8s.apps.v1.Deployment(
        f"{name}-deployment",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name=name,
            namespace=namespace.metadata.name,
            labels={"app": name}
        ),
        spec=k8s.apps.v1.DeploymentSpecArgs(
            replicas=replicas,
            selector=k8s.meta.v1.LabelSelectorArgs(
                match_labels={"app": name}
            ),
            template=k8s.core.v1.PodTemplateSpecArgs(
                metadata=k8s.meta.v1.ObjectMetaArgs(
                    labels={"app": name}
                ),
                spec=k8s.core.v1.PodSpecArgs(
                    containers=[k8s.core.v1.ContainerArgs(
                        name=name,
                        image=image,
                        ports=[k8s.core.v1.ContainerPortArgs(
                            container_port=port,
                            name="http"
                        )],
                        env_from=[
                            k8s.core.v1.EnvFromSourceArgs(
                                config_map_ref=k8s.core.v1.ConfigMapEnvSourceArgs(
                                    name=config_map.metadata.name
                                )
                            ),
                        ],
                        resources=k8s.core.v1.ResourceRequirementsArgs(
                            requests={"cpu": cpu_request, "memory": memory_request},
                            limits={"cpu": cpu_limit, "memory": memory_limit}
                        ),
                        liveness_probe=k8s.core.v1.ProbeArgs(
                            http_get=k8s.core.v1.HTTPGetActionArgs(
                                path="/health",
                                port=port
                            ),
                            initial_delay_seconds=30,
                            period_seconds=10,
                        ),
                        readiness_probe=k8s.core.v1.ProbeArgs(
                            http_get=k8s.core.v1.HTTPGetActionArgs(
                                path="/health",
                                port=port
                            ),
                            initial_delay_seconds=5,
                            period_seconds=5,
                        ),
                    )]
                )
            )
        ),
        opts=pulumi.ResourceOptions(
            provider=provider,
            depends_on=[namespace, config_map]
        )
    )


def create_rag_deployment(
    provider: k8s.Provider,
    namespace: k8s.core.v1.Namespace,
    config_map: k8s.core.v1.ConfigMap,
    secret: k8s.core.v1.Secret,
    image: str,
):
    """Create RAG deployment with Gemini API key"""
    
    return k8s.apps.v1.Deployment(
        "rag-deployment",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="rag",
            namespace=namespace.metadata.name,
            labels={"app": "rag"}
        ),
        spec=k8s.apps.v1.DeploymentSpecArgs(
            replicas=2,
            selector=k8s.meta.v1.LabelSelectorArgs(
                match_labels={"app": "rag"}
            ),
            template=k8s.core.v1.PodTemplateSpecArgs(
                metadata=k8s.meta.v1.ObjectMetaArgs(
                    labels={"app": "rag"}
                ),
                spec=k8s.core.v1.PodSpecArgs(
                    containers=[k8s.core.v1.ContainerArgs(
                        name="rag",
                        image=image,
                        ports=[k8s.core.v1.ContainerPortArgs(
                            container_port=8003,
                            name="http"
                        )],
                        env=[
                            k8s.core.v1.EnvVarArgs(name="PORT", value="8003"),
                            k8s.core.v1.EnvVarArgs(
                                name="GEMINI_API_KEY",
                                value_from=k8s.core.v1.EnvVarSourceArgs(
                                    secret_key_ref=k8s.core.v1.SecretKeySelectorArgs(
                                        name=secret.metadata.name,
                                        key="GEMINI_API_KEY"
                                    )
                                )
                            ),
                        ],
                        env_from=[
                            k8s.core.v1.EnvFromSourceArgs(
                                config_map_ref=k8s.core.v1.ConfigMapEnvSourceArgs(
                                    name=config_map.metadata.name
                                )
                            ),
                        ],
                        resources=k8s.core.v1.ResourceRequirementsArgs(
                            requests={"cpu": "250m", "memory": "1Gi"},
                            limits={"cpu": "1000m", "memory": "4Gi"}
                        ),
                        liveness_probe=k8s.core.v1.ProbeArgs(
                            http_get=k8s.core.v1.HTTPGetActionArgs(
                                path="/health",
                                port=8003
                            ),
                            initial_delay_seconds=30,
                            period_seconds=10,
                        ),
                        readiness_probe=k8s.core.v1.ProbeArgs(
                            http_get=k8s.core.v1.HTTPGetActionArgs(
                                path="/health",
                                port=8003
                            ),
                            initial_delay_seconds=5,
                            period_seconds=5,
                        ),
                    )]
                )
            )
        ),
        opts=pulumi.ResourceOptions(
            provider=provider,
            depends_on=[namespace, config_map, secret]
        )
    )


def create_chromadb_deployment(
    provider: k8s.Provider,
    namespace: k8s.core.v1.Namespace,
    image: str,
):
    """Create ChromaDB deployment"""
    
    return k8s.apps.v1.Deployment(
        "chromadb-deployment",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="chromadb",
            namespace=namespace.metadata.name,
            labels={"app": "chromadb"}
        ),
        spec=k8s.apps.v1.DeploymentSpecArgs(
            replicas=1,
            selector=k8s.meta.v1.LabelSelectorArgs(
                match_labels={"app": "chromadb"}
            ),
            template=k8s.core.v1.PodTemplateSpecArgs(
                metadata=k8s.meta.v1.ObjectMetaArgs(
                    labels={"app": "chromadb"}
                ),
                spec=k8s.core.v1.PodSpecArgs(
                    containers=[k8s.core.v1.ContainerArgs(
                        name="chromadb",
                        image=image,
                        ports=[k8s.core.v1.ContainerPortArgs(
                            container_port=8000,
                            name="http"
                        )],
                        env=[
                            k8s.core.v1.EnvVarArgs(
                                name="ANONYMIZED_TELEMETRY",
                                value="False"
                            ),
                        ],
                        resources=k8s.core.v1.ResourceRequirementsArgs(
                            requests={"cpu": "250m", "memory": "512Mi"},
                            limits={"cpu": "500m", "memory": "1Gi"}
                        ),
                    )]
                )
            )
        ),
        opts=pulumi.ResourceOptions(
            provider=provider,
            depends_on=[namespace]
        )
    )


def create_frontend_deployment(
    provider: k8s.Provider,
    namespace: k8s.core.v1.Namespace,
    image: str,
    api_url: str,
):
    """Create Frontend deployment"""
    
    return k8s.apps.v1.Deployment(
        "frontend-deployment",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="frontend",
            namespace=namespace.metadata.name,
            labels={"app": "frontend"}
        ),
        spec=k8s.apps.v1.DeploymentSpecArgs(
            replicas=2,
            selector=k8s.meta.v1.LabelSelectorArgs(
                match_labels={"app": "frontend"}
            ),
            template=k8s.core.v1.PodTemplateSpecArgs(
                metadata=k8s.meta.v1.ObjectMetaArgs(
                    labels={"app": "frontend"}
                ),
                spec=k8s.core.v1.PodSpecArgs(
                    containers=[k8s.core.v1.ContainerArgs(
                        name="frontend",
                        image=image,
                        ports=[k8s.core.v1.ContainerPortArgs(
                            container_port=3000,
                            name="http"
                        )],
                        env=[
                            k8s.core.v1.EnvVarArgs(
                                name="NEXT_PUBLIC_API_URL",
                                value=api_url
                            ),
                        ],
                        resources=k8s.core.v1.ResourceRequirementsArgs(
                            requests={"cpu": "250m", "memory": "512Mi"},
                            limits={"cpu": "500m", "memory": "1Gi"}
                        ),
                    )]
                )
            )
        ),
        opts=pulumi.ResourceOptions(
            provider=provider,
            depends_on=[namespace]
        )
    )


def create_all_deployments(
    provider: k8s.Provider,
    namespace: k8s.core.v1.Namespace,
    config_map: k8s.core.v1.ConfigMap,
    secret: k8s.core.v1.Secret,
    project_id: str,
    api_url: str = "http://localhost/api",
) -> dict:
    """Create all deployments"""
    
    registry = f"us-central1-docker.pkg.dev/{project_id}/agriguard"
    
    return {
        'mcsi': create_deployment_with_gcp_creds(
            provider, namespace, config_map, secret,
            "mcsi", f"{registry}/mcsi:latest", 8000
        ),
        'yield': create_deployment_with_gcp_creds(
            provider, namespace, config_map, secret,
            "yield", f"{registry}/yield:latest", 8001
        ),
        'api': create_deployment_basic(
            provider, namespace, config_map,
            "api", f"{registry}/api:latest", 8000
        ),
        'chromadb': create_chromadb_deployment(
            provider, namespace, f"{registry}/chromadb:0.4.24"
        ),
        'rag': create_rag_deployment(
            provider, namespace, config_map, secret,
            f"{registry}/rag:latest"
        ),
        'frontend': create_frontend_deployment(
            provider, namespace, f"{registry}/frontend:latest", api_url
        ),
    }
