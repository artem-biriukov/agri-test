"""AgriGuard Infrastructure - Main Program"""
import pulumi
from gcp import create_gke_cluster, get_kubeconfig, create_k8s_provider
from kubernetes.config import create_namespace, create_configmap, create_secrets
from kubernetes.deployments import create_all_deployments
from kubernetes.services import create_all_services
from kubernetes.ingress import create_ingress

# Get configuration
config = pulumi.Config()
gcp_config = pulumi.Config("gcp")

project_id = gcp_config.require("project")
region = gcp_config.require("region")
gemini_api_key = config.require_secret("geminiApiKey")
gcp_sa_key_json = config.require_secret("gcpServiceAccountKey")

# Create GKE Cluster
cluster = create_gke_cluster(project_id, region)

# Create Kubernetes provider
k8s_provider = create_k8s_provider(cluster)

# Create Namespace
namespace = create_namespace(k8s_provider)

# Create ConfigMap and Secrets
config_map = create_configmap(k8s_provider, namespace)
secret = create_secrets(k8s_provider, namespace, gemini_api_key, gcp_sa_key_json)

# Create Deployments
deployments = create_all_deployments(
    k8s_provider,
    namespace,
    config_map,
    secret,
    project_id,
    api_url="http://localhost/api"
)

# Create Services
services = create_all_services(k8s_provider, namespace, deployments)

# Create Ingress
ingress = create_ingress(k8s_provider, namespace, services)

# Exports
pulumi.export("cluster_name", cluster.name)
pulumi.export("cluster_endpoint", cluster.endpoint)
pulumi.export("kubeconfig", get_kubeconfig(cluster))

pulumi.export("ingress_ip", ingress.status.apply(
    lambda status: status.load_balancer.ingress[0].ip
    if status and status.load_balancer and status.load_balancer.ingress
    else "Pending..."
))

pulumi.export("application_url", ingress.status.apply(
    lambda status: f"http://{status.load_balancer.ingress[0].ip}"
    if status and status.load_balancer and status.load_balancer.ingress
    else "Pending ingress IP allocation..."
))

pulumi.export("next_steps", """
✅ Deployment complete!

Next steps:
1. Get ingress IP: pulumi stack output ingress_ip
2. Update frontend: 
   INGRESS_IP=$(pulumi stack output ingress_ip)
   kubectl set env deployment/frontend -n agriguard NEXT_PUBLIC_API_URL=http://$INGRESS_IP/api
   kubectl rollout restart deployment/frontend -n agriguard
3. Access app: pulumi stack output application_url
""")
