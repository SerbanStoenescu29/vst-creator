#pragma once

#include <JuceHeader.h>
#include "PluginProcessor.h"

class VstAiDemoAudioProcessorEditor final : public juce::AudioProcessorEditor
{
public:
    explicit VstAiDemoAudioProcessorEditor(VstAiDemoAudioProcessor&);
    ~VstAiDemoAudioProcessorEditor() override = default;

    void paint(juce::Graphics&) override;
    void resized() override;

private:
    VstAiDemoAudioProcessor& processor;
    
    juce::Slider delayTimeSlider;
    juce::Slider feedbackSlider;
    juce::Slider mixSlider;
    
    juce::Label delayTimeLabel;
    juce::Label feedbackLabel;
    juce::Label mixLabel;
    
    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> delayTimeAttachment;
    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> feedbackAttachment;
    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> mixAttachment;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(VstAiDemoAudioProcessorEditor)
};
