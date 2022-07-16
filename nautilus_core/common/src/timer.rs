// -------------------------------------------------------------------------------------------------
//  Copyright (C) 2015-2022 Nautech Systems Pty Ltd. All rights reserved.
//  https://nautechsystems.io
//
//  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
//  You may not use this file except in compliance with the License.
//  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
//
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.
// -------------------------------------------------------------------------------------------------

use crate::enums::MessageCategory;
use nautilus_core::string::{pystr_to_string, string_to_pystr};
use nautilus_core::time::{Timedelta, Timestamp};
use nautilus_core::uuid::UUID4;
use pyo3::ffi;
use pyo3::prelude::*;

#[repr(C)]
#[pyclass]
#[derive(Clone, Debug)]
/// Represents a time event occurring at the event timestamp.
pub struct TimeEvent {
    /// The event name.
    pub name: Box<String>,
    /// The event ID.
    pub category: MessageCategory, // Only applicable to generic messages in the future
    /// The UNIX timestamp (nanoseconds) when the time event occurred.
    pub event_id: UUID4,
    /// The message category
    pub ts_event: Timestamp,
    /// The UNIX timestamp (nanoseconds) when the object was initialized.
    pub ts_init: Timestamp,
}

impl PartialEq for TimeEvent {
    fn eq(&self, other: &Self) -> bool {
        self.name == other.name && self.ts_event == other.ts_event
    }
}

////////////////////////////////////////////////////////////////////////////////
// C API
////////////////////////////////////////////////////////////////////////////////
#[no_mangle]
pub extern "C" fn time_event_free(event: TimeEvent) {
    drop(event); // Memory freed here
}

/// # Safety
/// - `name` must be borrowed from a valid Python UTF-8 `str`.
#[no_mangle]
pub unsafe extern "C" fn time_event_new(
    name: *mut ffi::PyObject,
    event_id: UUID4,
    ts_event: u64,
    ts_init: u64,
) -> TimeEvent {
    TimeEvent {
        name: Box::new(pystr_to_string(name)),
        category: MessageCategory::EVENT,
        event_id,
        ts_event,
        ts_init,
    }
}

/// Returns a pointer to a valid Python UTF-8 string.
///
/// # Safety
/// - Assumes that since the data is originating from Rust, the GIL does not need
/// to be acquired.
/// - Assumes you are immediately returning this pointer to Python.
#[no_mangle]
pub unsafe extern "C" fn time_event_name(event: &TimeEvent) -> *mut ffi::PyObject {
    string_to_pystr(event.name.as_str())
}

/// Represents a bundled event and it's handler.
#[repr(C)]
#[pyclass]
#[derive(Clone)]
pub struct TimeEventHandler {
    /// A [TimeEvent] generated by a timer.
    pub event: TimeEvent,
    /// A callable handler for this time event.
    pub handler: PyObject,
}

// impl TimeEventHandler {
//     #[inline]
//     pub fn handle_py(self) {
//         Python::with_gil(|py| {
//             self.handler
//                 .call0(py).
//                 expect("Failed calling handler");
//         });
//     }
//
//     #[inline]
//     pub fn handle(self) {
//         Python::with_gil(|py| {
//             self.handler
//                 .call1(py, (self.event,))
//                 .expect("Failed calling handler");
//         });
//     }
// }

pub trait Timer {
    fn new(
        name: PyObject,
        interval_ns: Timedelta,
        start_time_ns: Timestamp,
        stop_time_ns: Option<Timestamp>,
    ) -> Self;
    fn pop_event(&self, event_id: UUID4, ts_init: Timestamp) -> TimeEvent;
    fn iterate_next_time(&mut self, ts_now: Timestamp);
    fn cancel(&mut self);
}

#[allow(dead_code)]
pub struct TestTimer {
    name: String,
    interval_ns: Timedelta,
    start_time_ns: Timestamp,
    stop_time_ns: Option<Timestamp>,
    pub next_time_ns: Timestamp,
    pub is_expired: bool,
}

impl TestTimer {
    pub fn new(
        name: String,
        interval_ns: Timedelta,
        start_time_ns: Timestamp,
        stop_time_ns: Option<Timestamp>,
    ) -> Self {
        TestTimer {
            name,
            interval_ns,
            start_time_ns,
            stop_time_ns,
            next_time_ns: start_time_ns + interval_ns as u64,
            is_expired: false,
        }
    }

    pub fn pop_event(&self, event_id: UUID4, ts_init: Timestamp) -> TimeEvent {
        TimeEvent {
            name: Box::new(self.name.clone()),
            category: MessageCategory::EVENT,
            event_id,
            ts_event: self.next_time_ns,
            ts_init,
        }
    }

    /// Advance the test timer forward to the given time, generating a sequence
    /// of events. A [TimeEvent] is appended for each time a next event is
    /// <= the given `to_time_ns`.
    pub fn advance(&mut self, to_time_ns: Timestamp) -> impl Iterator<Item = TimeEvent> + '_ {
        self.take_while(move |(_, next_time_ns)| to_time_ns >= *next_time_ns)
            .map(|(event, _)| event)
    }

    // TODO(cs): Potentially now redundant with the iterator
    /// Iterates the timers next time, and checks if the timer is now expired.
    // pub fn iterate_next_time(&mut self, ts_now: Timestamp) {
    //     self.next_time_ns += self.interval_ns as u64;
    //     if let Some(stop_time_ns) = self.stop_time_ns {
    //         if ts_now >= stop_time_ns {
    //             self.is_expired = true
    //         }
    //     }
    // }

    /// Cancels the timer (the timer will not generate an event).
    pub fn cancel(&mut self) {
        self.is_expired = true;
    }
}

impl Iterator for TestTimer {
    type Item = (TimeEvent, Timestamp);

    fn next(&mut self) -> Option<Self::Item> {
        if self.is_expired {
            None
        } else {
            let item = (
                TimeEvent {
                    name: Box::new(self.name.clone()),
                    category: MessageCategory::EVENT,
                    event_id: UUID4::new(),
                    ts_event: self.next_time_ns,
                    ts_init: self.next_time_ns,
                },
                self.next_time_ns,
            );

            // If current next event time has exceeded stop time, then expire timer
            if let Some(stop_time_ns) = self.stop_time_ns {
                if self.next_time_ns >= stop_time_ns {
                    self.is_expired = true;
                }
            }

            self.next_time_ns += self.interval_ns as u64;

            Some(item)
        }
    }
}

////////////////////////////////////////////////////////////////////////////////
// Tests
////////////////////////////////////////////////////////////////////////////////
#[cfg(test)]
mod tests {
    use super::{TestTimer, TimeEvent};

    #[test]
    fn test_pop_event() {
        let name = String::from("test_timer");
        let mut timer = TestTimer::new(name, 0, 1, None);

        assert!(timer.next().is_some());
        assert!(timer.next().is_some());
        timer.is_expired = true;
        assert!(timer.next().is_none());
    }

    #[test]
    fn test_advance() {
        let name = String::from("test_timer");
        let mut timer = TestTimer::new(name, 1, 0, None);
        let events: Vec<TimeEvent> = timer.advance(5).collect();

        assert_eq!(events.len(), 5);
    }

    #[test]
    fn test_advance_stop() {
        let name = String::from("test_timer");
        let mut timer = TestTimer::new(name, 1, 0, Some(5));
        let events: Vec<TimeEvent> = timer.advance(10).collect();

        assert_eq!(events.len(), 5);
    }
}
