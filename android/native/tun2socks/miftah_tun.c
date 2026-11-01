/*
 * JNI bridge between com.miftah.vpn.xray.Tun2Socks and hev-socks5-tunnel.
 *
 * The tunnel is configured from a YAML string generated here, so the app does
 * not need to ship a config file. The TUN fd comes from VpnService.establish().
 */
#include <jni.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>

#include "hev-socks5-tunnel.h"

static pthread_t g_thread;
static volatile int g_running = 0;
static int g_fd = -1;
static int g_port = 10808;
static char g_dns[64] = "1.1.1.1";

static void *tunnel_main(void *arg) {
    (void) arg;
    char yaml[1024];
    snprintf(
        yaml,
        sizeof(yaml),
        "tunnel:\n"
        "  name: tun0\n"
        "  mtu: 1500\n"
        "  multi-queue: false\n"
        "socks5:\n"
        "  port: %d\n"
        "  address: 127.0.0.1\n"
        "  udp: 'udp'\n"
        "mapdns:\n"
        "  address: %s\n"
        "  port: 53\n"
        "  network: 'udp'\n"
        "  proxy: false\n"
        "misc:\n"
        "  task-stack-size: 20480\n",
        g_port,
        g_dns);

    hev_socks5_tunnel_main_from_str(
        (const unsigned char *) yaml,
        (unsigned int) strlen(yaml),
        g_fd);

    g_running = 0;
    return NULL;
}

JNIEXPORT jint JNICALL
Java_com_miftah_vpn_xray_Tun2Socks_nativeStart(
    JNIEnv *env, jobject thiz, jint tun_fd, jint socks_port, jstring dns) {
    (void) thiz;
    if (g_running) {
        return -1;
    }
    if (dns != NULL) {
        const char *d = (*env)->GetStringUTFChars(env, dns, NULL);
        if (d != NULL) {
            strncpy(g_dns, d, sizeof(g_dns) - 1);
            g_dns[sizeof(g_dns) - 1] = '\0';
            (*env)->ReleaseStringUTFChars(env, dns, d);
        }
    }
    g_fd = (int) tun_fd;
    g_port = (int) socks_port;
    g_running = 1;
    if (pthread_create(&g_thread, NULL, tunnel_main, NULL) != 0) {
        g_running = 0;
        return -2;
    }
    return 0;
}

JNIEXPORT void JNICALL
Java_com_miftah_vpn_xray_Tun2Socks_nativeStop(JNIEnv *env, jobject thiz) {
    (void) env;
    (void) thiz;
    if (!g_running) {
        return;
    }
    hev_socks5_tunnel_quit();
    pthread_join(g_thread, NULL);
    g_running = 0;
}
