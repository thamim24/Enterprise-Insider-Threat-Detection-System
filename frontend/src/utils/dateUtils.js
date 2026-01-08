/**
 * Date formatting utilities for Indian Standard Time (IST)
 * Backend stores timestamps in UTC - we convert to IST (UTC+5:30)
 */

// IST offset from UTC in milliseconds (5 hours 30 minutes)
const IST_OFFSET_MS = (5 * 60 + 30) * 60 * 1000;

/**
 * Convert UTC date to IST
 * @param {string|Date} date - UTC date
 * @returns {Date} Date adjusted to IST
 */
function toIST(date) {
  const d = new Date(date);
  // If the date string doesn't end with 'Z', treat it as UTC and add Z
  if (typeof date === 'string' && !date.endsWith('Z') && !date.includes('+')) {
    return new Date(new Date(date + 'Z').getTime() + IST_OFFSET_MS);
  }
  // If it's already a proper UTC date, just add IST offset
  return new Date(d.getTime() + IST_OFFSET_MS);
}

/**
 * Format date with full date and time in IST format
 * @param {string|Date} date - Date to format (UTC from backend)
 * @returns {string} Formatted date string (DD/MM/YYYY, HH:MM:SS IST)
 */
export function formatDateTimeIST(date) {
  if (!date) return 'N/A';
  
  try {
    const d = toIST(date);
    const day = String(d.getUTCDate()).padStart(2, '0');
    const month = String(d.getUTCMonth() + 1).padStart(2, '0');
    const year = d.getUTCFullYear();
    const hours = String(d.getUTCHours()).padStart(2, '0');
    const minutes = String(d.getUTCMinutes()).padStart(2, '0');
    const seconds = String(d.getUTCSeconds()).padStart(2, '0');
    
    return `${day}/${month}/${year}, ${hours}:${minutes}:${seconds} IST`;
  } catch (error) {
    console.error('Date formatting error:', error);
    return String(date);
  }
}

/**
 * Format time only in IST format
 * @param {string|Date} date - Date to format (UTC from backend)
 * @returns {string} Formatted time string (HH:MM:SS IST)
 */
export function formatTimeIST(date) {
  if (!date) return 'N/A';
  
  try {
    const d = toIST(date);
    const hours = String(d.getUTCHours()).padStart(2, '0');
    const minutes = String(d.getUTCMinutes()).padStart(2, '0');
    const seconds = String(d.getUTCSeconds()).padStart(2, '0');
    
    return `${hours}:${minutes}:${seconds} IST`;
  } catch (error) {
    console.error('Time formatting error:', error);
    return String(date);
  }
}

/**
 * Format date only in IST format
 * @param {string|Date} date - Date to format (UTC from backend)
 * @returns {string} Formatted date string (DD/MM/YYYY)
 */
export function formatDateIST(date) {
  if (!date) return 'N/A';
  
  try {
    const d = toIST(date);
    const day = String(d.getUTCDate()).padStart(2, '0');
    const month = String(d.getUTCMonth() + 1).padStart(2, '0');
    const year = d.getUTCFullYear();
    
    return `${day}/${month}/${year}`;
  } catch (error) {
    console.error('Date formatting error:', error);
    return String(date);
  }
}

/**
 * Format date for short display (e.g., "08 Jan 2026, 21:30 IST")
 * @param {string|Date} date - Date to format (UTC from backend)
 * @returns {string} Short formatted date string
 */
export function formatShortDateTimeIST(date) {
  if (!date) return 'N/A';
  
  try {
    const d = toIST(date);
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const day = String(d.getUTCDate()).padStart(2, '0');
    const month = months[d.getUTCMonth()];
    const year = d.getUTCFullYear();
    const hours = String(d.getUTCHours()).padStart(2, '0');
    const minutes = String(d.getUTCMinutes()).padStart(2, '0');
    
    return `${day} ${month} ${year}, ${hours}:${minutes} IST`;
  } catch (error) {
    console.error('Date formatting error:', error);
    return String(date);
  }
}

/**
 * Get current date in IST
 * @returns {Date} Current date adjusted for display purposes
 */
export function getCurrentDateIST() {
  return new Date();
}

export default {
  formatDateTimeIST,
  formatTimeIST,
  formatDateIST,
  formatShortDateTimeIST,
  getCurrentDateIST,
};
