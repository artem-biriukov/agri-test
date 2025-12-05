"""GKE Autopilot cluster provisioning"""
import pulumi
import pulumi_gcp as gcp
import pulumi_kubernetes as k8s


def create_gke_cluster(project_id: str, region: str) -> gcp.container.Cluster:
    """Create GKE Autopilot cluster"""
    
    cluster = gcp.container.Cluster(
        "agriguard-cluster",
        name="agriguard-cluster",
        location=region,
        enable_autopilot=True,
        ip_allocation_policy=gcp.container.ClusterIpAllocationPolicyArgs(
            cluster_ipv4_cidr_block="/17",
            services_ipv4_cidr_block="/22",
        ),
        release_channel=gcp.container.ClusterReleaseChannelArgs(
            channel="REGULAR",
        ),
        deletion_protection=False,
    )
    
    return cluster


def get_kubeconfig(cluster: gcp.container.Cluster) -> pulumi.Output[str]:
    """Generate kubeconfig for accessing the cluster"""
    
    return pulumi.Output.all(
        cluster.name,
        cluster.endpoint,
        cluster.master_auth
    ).apply(lambda args: f"""apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: {args[2].cluster_ca_certificate}
    server: https://{args[1]}
  name: {args[0]}
contexts:
- context:
    cluster: {args[0]}
    user: {args[0]}
  name: {args[0]}
current-context: {args[0]}
kind: Config
users:
- name: {args[0]}
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      command: gke-gcloud-auth-plugin
      installHint: Install gke-gcloud-auth-plugin
      provideClusterInfo: true
""")


def create_k8s_provider(cluster: gcp.container.Cluster):
    """Create Kubernetes provider"""
    
    kubeconfig = get_kubeconfig(cluster)
    
    return k8s.Provider(
        "gke-k8s",
        kubeconfig=kubeconfig,
        opts=pulumi.ResourceOptions(depends_on=[cluster])
    )
