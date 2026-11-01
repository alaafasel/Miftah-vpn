package com.miftah.vpn.ui

import java.time.Instant
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

private val dateFmt: DateTimeFormatter = DateTimeFormatter.ofPattern("yyyy/MM/dd", Locale.US)

/** Formats an ISO-8601 timestamp coming from the API into a short local date. */
fun formatDate(raw: String?): String {
    if (raw.isNullOrBlank()) return "—"
    return runCatching {
        val instant = runCatching { Instant.parse(raw) }
            .getOrElse { OffsetDateTime.parse(raw).toInstant() }
        dateFmt.format(instant.atZone(ZoneId.systemDefault()))
    }.getOrElse { raw.take(10) }
}

/** Rounds remaining seconds up to whole days (1 hour left still shows "1"). */
fun remainingDays(seconds: Long): Long = if (seconds <= 0L) 0L else (seconds + 86_399L) / 86_400L
